import {
  App,
  Stack,
  StackProps,
  RemovalPolicy,
  Fn,
  CfnOutput
} from "aws-cdk-lib"
import {
  Bucket,
  BucketEncryption,
  BlockPublicAccess,
  ObjectOwnership
} from "aws-cdk-lib/aws-s3"
import {Key} from "aws-cdk-lib/aws-kms"
import {PolicyStatement} from "aws-cdk-lib/aws-iam"
import {
  CfnGuardrail,
  CfnGuardrailVersion,
  CfnKnowledgeBase,
  CfnDataSource
} from "aws-cdk-lib/aws-bedrock"
import {RestApiGateway} from "../constructs/RestApiGateway"
import {LambdaFunction} from "../constructs/LambdaFunction"
import {LambdaIntegration} from "aws-cdk-lib/aws-apigateway"
import * as iam from "aws-cdk-lib/aws-iam"
import * as ops from "aws-cdk-lib/aws-opensearchserverless"
import * as cr from "aws-cdk-lib/custom-resources"
import * as ssm from "aws-cdk-lib/aws-ssm"
import {nagSuppressions} from "../nagSuppressions"

export interface EpsAssistMeStackProps extends StackProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
}

export class EpsAssistMeStack extends Stack {
  public constructor(scope: App, id: string, props: EpsAssistMeStackProps) {
    super(scope, id, props)

    // ==== Context/Parameters ====
    const region = Stack.of(this).region
    const account = Stack.of(this).account
    const logRetentionInDays = Number(this.node.tryGetContext("logRetentionInDays")) || 14
    const logLevel: string = this.node.tryGetContext("logLevel")
    const slackBotToken: string = this.node.tryGetContext("slackBotToken")
    const slackSigningSecret: string = this.node.tryGetContext("slackSigningSecret")

    // ==== SSM Parameter Store for Slack Secrets ====
    const slackBotTokenParameter = new ssm.StringParameter(this, "SlackBotTokenParameter", {
      parameterName: "/eps-assist/slack/bot-token",
      stringValue: slackBotToken,
      description: "Slack Bot OAuth Token for EPS Assist",
      tier: ssm.ParameterTier.STANDARD
    })

    const slackSigningSecretParameter = new ssm.StringParameter(this, "SlackSigningSecretParameter", {
      parameterName: "/eps-assist/slack/signing-secret",
      stringValue: slackSigningSecret,
      description: "Slack Signing Secret for EPS Assist",
      tier: ssm.ParameterTier.STANDARD
    })

    // ==== KMS Key Import ====
    const cloudWatchLogsKmsKey = Key.fromKeyArn(
      this, "cloudWatchLogsKmsKey", Fn.importValue("account-resources:CloudwatchLogsKmsKeyArn")
    )

    // ==== S3 Buckets ====
    const accessLogBucket = new Bucket(this, "EpsAssistAccessLogsBucket", {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryption: BucketEncryption.KMS,
      encryptionKey: cloudWatchLogsKmsKey,
      removalPolicy: RemovalPolicy.RETAIN,
      autoDeleteObjects: true,
      enforceSSL: true,
      versioned: false,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED
    })

    const kbDocsBucket = new Bucket(this, "EpsAssistDocsBucket", {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryptionKey: cloudWatchLogsKmsKey,
      encryption: BucketEncryption.KMS,
      removalPolicy: RemovalPolicy.RETAIN,
      autoDeleteObjects: true,
      enforceSSL: true,
      versioned: true,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED,
      serverAccessLogsBucket: accessLogBucket,
      serverAccessLogsPrefix: "s3-access-logs/"
    })

    // ==== IAM Policies for S3 access (Bedrock Execution Role) ====
    const s3AccessListPolicy = new iam.PolicyStatement({
      actions: ["s3:ListBucket"],
      resources: [kbDocsBucket.bucketArn]
    })
    s3AccessListPolicy.addCondition("StringEquals", {"aws:ResourceAccount": account})

    const s3AccessGetPolicy = new iam.PolicyStatement({
      actions: ["s3:GetObject", "s3:Delete*"],
      resources: [`${kbDocsBucket.bucketArn}/*`]
    })
    s3AccessGetPolicy.addCondition("StringEquals", {"aws:ResourceAccount": account})

    // ==== IAM Policy to invoke Bedrock Embedding Model ====
    const EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
    const bedrockExecutionRolePolicy = new iam.PolicyStatement()
    bedrockExecutionRolePolicy.addActions("bedrock:InvokeModel")
    bedrockExecutionRolePolicy.addResources(`arn:aws:bedrock:${region}::foundation-model/${EMBEDDING_MODEL}`)

    // ==== IAM Policy to delete Bedrock knowledge base ====
    const bedrockKBDeleteRolePolicy = new iam.PolicyStatement()
    bedrockKBDeleteRolePolicy.addActions("bedrock:Delete*")
    bedrockKBDeleteRolePolicy.addResources(`arn:aws:bedrock:${region}:${account}:knowledge-base/*`)

    // ==== IAM Policy to call OpenSearchServerless (AOSS) ====
    const bedrockOSSPolicyForKnowledgeBase = new iam.PolicyStatement()
    bedrockOSSPolicyForKnowledgeBase.addActions("aoss:APIAccessAll")
    bedrockOSSPolicyForKnowledgeBase.addActions(
      "aoss:DeleteAccessPolicy",
      "aoss:DeleteCollection",
      "aoss:DeleteLifecyclePolicy",
      "aoss:DeleteSecurityConfig",
      "aoss:DeleteSecurityPolicy"
    )
    bedrockOSSPolicyForKnowledgeBase.addResources(`arn:aws:aoss:${region}:${account}:collection/*`)

    // ==== Bedrock Execution Role for Knowledge Base ====
    const bedrockKbRole = new iam.Role(this, "EpsAssistMeBedrockExecutionRole", {
      assumedBy: new iam.ServicePrincipal("bedrock.amazonaws.com"),
      description: "Role for Bedrock Knowledge Base to access S3 and OpenSearch"
    })
    bedrockKbRole.addToPolicy(bedrockExecutionRolePolicy)
    bedrockKbRole.addToPolicy(bedrockOSSPolicyForKnowledgeBase)
    bedrockKbRole.addToPolicy(s3AccessListPolicy)
    bedrockKbRole.addToPolicy(s3AccessGetPolicy)
    bedrockKbRole.addToPolicy(bedrockKBDeleteRolePolicy)

    // ==== Bedrock Guardrail and Version ====
    const guardrail = new CfnGuardrail(this, "EpsGuardrail", {
      name: "eps-assist-guardrail",
      description: "Guardrail for EPS Assist Me bot",
      blockedInputMessaging: "Your input was blocked.",
      blockedOutputsMessaging: "Your output was blocked.",
      contentPolicyConfig: {
        filtersConfig: [
          {type: "SEXUAL", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "VIOLENCE", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "HATE", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "INSULTS", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "MISCONDUCT", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "PROMPT_ATTACK", inputStrength: "HIGH", outputStrength: "NONE"}
        ]
      },
      sensitiveInformationPolicyConfig: {
        piiEntitiesConfig: [
          {type: "EMAIL", action: "ANONYMIZE"},
          {type: "PHONE", action: "ANONYMIZE"},
          {type: "NAME", action: "ANONYMIZE"},
          {type: "CREDIT_DEBIT_CARD_NUMBER", action: "BLOCK"}
        ]
      },
      wordPolicyConfig: {
        managedWordListsConfig: [{type: "PROFANITY"}]
      }
    })

    const guardrailVersion = new CfnGuardrailVersion(this, "EpsGuardrailVersion", {
      guardrailIdentifier: guardrail.attrGuardrailId,
      description: "Initial version"
    })

    // ==== OpenSearch Serverless: Security & Collection ====
    const osEncryptionPolicy = new ops.CfnSecurityPolicy(this, "OsEncryptionPolicy", {
      name: "eps-assist-encryption-policy",
      type: "encryption",
      policy: JSON.stringify({
        Rules: [{ResourceType: "collection", Resource: ["collection/eps-assist-vector-db"]}],
        AWSOwnedKey: true
      })
    })

    const osCollection = new ops.CfnCollection(this, "OsCollection", {
      name: "eps-assist-vector-db",
      description: "EPS Assist Vector Store",
      type: "VECTORSEARCH"
    })
    osCollection.addDependency(osEncryptionPolicy)

    const osNetworkPolicy = new ops.CfnSecurityPolicy(this, "OsNetworkPolicy", {
      name: "eps-assist-network-policy",
      type: "network",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: ["collection/eps-assist-vector-db"]},
          {ResourceType: "dashboard", Resource: ["collection/eps-assist-vector-db"]}
        ],
        AllowFromPublic: true
      }])
    })
    osCollection.addDependency(osNetworkPolicy)

    // ==== Lambda Role for Creating OpenSearch Index ====
    const createIndexFunctionRole = new iam.Role(this, "CreateIndexFunctionRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      description: "Lambda role for creating OpenSearch index"
    })
    createIndexFunctionRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole")
    )
    createIndexFunctionRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        "aoss:APIAccessAll",
        "aoss:DescribeIndex",
        "aoss:ReadDocument",
        "aoss:CreateIndex",
        "aoss:DeleteIndex",
        "aoss:UpdateIndex",
        "aoss:WriteDocument",
        "aoss:CreateCollectionItems",
        "aoss:DeleteCollectionItems",
        "aoss:UpdateCollectionItems",
        "aoss:DescribeCollectionItems"
      ],
      resources: [
        `arn:aws:aoss:${region}:${account}:collection/*`,
        `arn:aws:aoss:${region}:${account}:index/*`
      ]
    }))

    // ==== Lambda to Create OpenSearch Index ====
    const createIndexFunction = new LambdaFunction(this, "CreateIndexFunction", {
      stackName: props.stackName,
      functionName: `${props.stackName}-CreateIndexFunction`,
      packageBasePath: "packages/createIndexFunction",
      entryPoint: "app.py",
      logRetentionInDays,
      logLevel,
      environmentVariables: {"INDEX_NAME": osCollection.attrId},
      additionalPolicies: []
    })

    // ==== OpenSearchServerless access policy ====
    new ops.CfnAccessPolicy(this, "OsAccessPolicy", {
      name: "eps-assist-access-policy",
      type: "data",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: ["collection/*"], Permission: ["aoss:*"]},
          {ResourceType: "index", Resource: ["index/*/*"], Permission: ["aoss:*"]}
        ],
        Principal: [
          bedrockKbRole.roleArn,
          createIndexFunction.function.role?.roleArn,
          `arn:aws:iam::${account}:root`
        ]
      }])
    })

    // ==== Custom Resource to create vector index via Lambda ====
    const endpoint = `${osCollection.attrId}.${region}.aoss.amazonaws.com`
    const vectorIndex = new cr.AwsCustomResource(this, "VectorIndex", {
      installLatestAwsSdk: true,
      onCreate: {
        service: "Lambda",
        action: "invoke",
        parameters: {
          FunctionName: createIndexFunction.function.functionName,
          InvocationType: "RequestResponse",
          Payload: JSON.stringify({
            RequestType: "Create",
            CollectionName: osCollection.name,
            IndexName: "eps-assist-os-index",
            Endpoint: endpoint
          })
        },
        physicalResourceId: cr.PhysicalResourceId.of("VectorIndex-eps-assist-os-index")
      },
      onDelete: {
        service: "Lambda",
        action: "invoke",
        parameters: {
          FunctionName: createIndexFunction.function.functionName,
          InvocationType: "RequestResponse",
          Payload: JSON.stringify({
            RequestType: "Delete",
            CollectionName: osCollection.name,
            IndexName: "eps-assist-os-index",
            Endpoint: endpoint
          })
        }
      },
      policy: cr.AwsCustomResourcePolicy.fromStatements([
        new iam.PolicyStatement({
          actions: ["lambda:InvokeFunction"],
          resources: [createIndexFunction.function.functionArn]
        })
      ])
    })
    vectorIndex.node.addDependency(osCollection)

    // ==== Bedrock Knowledge Base Resource ====
    const kb = new CfnKnowledgeBase(this, "EpsKb", {
      name: "eps-assist-kb",
      description: "EPS Assist Knowledge Base",
      roleArn: bedrockKbRole.roleArn,
      knowledgeBaseConfiguration: {
        type: "VECTOR",
        vectorKnowledgeBaseConfiguration: {
          embeddingModelArn: `arn:aws:bedrock:${region}::foundation-model/${EMBEDDING_MODEL}`
        }
      },
      storageConfiguration: {
        type: "OPENSEARCH_SERVERLESS",
        opensearchServerlessConfiguration: {
          collectionArn: osCollection.attrArn,
          vectorIndexName: "eps-assist-os-index",
          fieldMapping: {
            vectorField: "bedrock-knowledge-base-default-vector",
            textField: "AMAZON_BEDROCK_TEXT_CHUNK",
            metadataField: "AMAZON_BEDROCK_METADATA"
          }
        }
      }
    })
    kb.node.addDependency(vectorIndex)

    // ==== S3 DataSource for Knowledge Base ====
    const kbDataSource = new CfnDataSource(this, "EpsKbDataSource", {
      name: "eps-assist-kb-ds",
      knowledgeBaseId: kb.attrKnowledgeBaseId,
      dataSourceConfiguration: {
        type: "S3",
        s3Configuration: {
          bucketArn: kbDocsBucket.bucketArn
        }
      }
    })
    kbDataSource.node.addDependency(kb)

    // ==== SlackBot Lambda Role Policies ====
    const slackLambdaSSMPolicy = new PolicyStatement({
      actions: ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParameterHistory"],
      resources: [
        slackBotTokenParameter.parameterArn,
        slackSigningSecretParameter.parameterArn
      ]
    })

    // ==== Lambda environment variables ====
    const lambdaEnv: {[key: string]: string} = {
      RAG_MODEL_ID: "anthropic.claude-3-sonnet-20240229-v1:0",
      EMBEDDING_MODEL: EMBEDDING_MODEL,
      SLACK_SLASH_COMMAND: "/ask-eps",
      COLLECTION_NAME: "eps-assist-vector-db",
      VECTOR_INDEX_NAME: "eps-assist-os-index",
      BEDROCK_KB_NAME: "eps-assist-kb",
      BEDROCK_KB_DATA_SOURCE: "eps-assist-kb-ds",
      LAMBDA_MEMORY_SIZE: "265",
      KNOWLEDGEBASE_ID: kb.attrKnowledgeBaseId,
      GUARD_RAIL_ID: guardrail.attrGuardrailId,
      GUARD_RAIL_VERSION: guardrailVersion.attrVersion,
      SLACK_BOT_TOKEN_PARAMETER: slackBotTokenParameter.parameterName,
      SLACK_SIGNING_SECRET_PARAMETER: slackSigningSecretParameter.parameterName
    }

    // ==== SlackBot Lambda ====
    const slackBotLambda = new LambdaFunction(this, "SlackBotLambda", {
      stackName: props.stackName,
      functionName: `${props.stackName}-SlackBotFunction`,
      packageBasePath: "packages/slackBotFunction",
      entryPoint: "app.py",
      logRetentionInDays,
      logLevel,
      environmentVariables: lambdaEnv,
      additionalPolicies: []
    })
    slackBotLambda.function.addToRolePolicy(slackLambdaSSMPolicy)

    // ==== API Gateway & Slack Route ====
    const apiGateway = new RestApiGateway(this, "EpsAssistApiGateway", {
      stackName: props.stackName,
      logRetentionInDays,
      enableMutualTls: false,
      trustStoreKey: "unused",
      truststoreVersion: "unused"
    })
    const slackRoute = apiGateway.api.root.addResource("slack").addResource("ask-eps")
    slackRoute.addMethod("POST", new LambdaIntegration(slackBotLambda.function, {
      credentialsRole: apiGateway.role
    }))
    apiGateway.role.addManagedPolicy(slackBotLambda.executionPolicy)

    // ==== Output: SlackBot Endpoint ====
    new CfnOutput(this, "SlackBotEndpoint", {
      value: `https://${apiGateway.api.domainName?.domainName}/slack/ask-eps`
    })

    // ==== Final CDK Nag Suppressions ====
    nagSuppressions(this)
  }
}
