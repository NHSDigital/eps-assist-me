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
import {Role, ServicePrincipal, PolicyStatement} from "aws-cdk-lib/aws-iam"
import {
  CfnGuardrail,
  CfnGuardrailVersion,
  CfnKnowledgeBase,
  CfnDataSource
} from "aws-cdk-lib/aws-bedrock"
import {RestApiGateway} from "../resources/RestApiGateway"
import {LambdaFunction} from "../resources/LambdaFunction"
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
    // Store Slack Bot Token and Signing Secret in SSM Parameters (encrypted)
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
    // Access logs bucket for S3
    const accessLogBucket = new Bucket(this, "EpsAssistAccessLogsBucket", {
      encryption: BucketEncryption.KMS,
      encryptionKey: cloudWatchLogsKmsKey,
      removalPolicy: RemovalPolicy.DESTROY,
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED
    })

    // S3 bucket for Bedrock Knowledge Base documents
    const kbDocsBucket = new Bucket(this, "EpsAssistDocsBucket", {
      encryptionKey: cloudWatchLogsKmsKey,
      encryption: BucketEncryption.KMS,
      removalPolicy: RemovalPolicy.DESTROY,
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED,
      serverAccessLogsBucket: accessLogBucket,
      serverAccessLogsPrefix: "s3-access-logs/"
    })

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
          {type: "HATE", inputStrength: "HIGH", outputStrength: "HIGH"}
        ]
      },
      sensitiveInformationPolicyConfig: {
        piiEntitiesConfig: [
          {type: "EMAIL", action: "ANONYMIZE"},
          {type: "NAME", action: "ANONYMIZE"}
        ]
      },
      wordPolicyConfig: {
        managedWordListsConfig: [{type: "PROFANITY"}]
      }
    })

    // Add metadata to the guardrail for cfn-guard compliance
    const guardrailVersion = new CfnGuardrailVersion(this, "EpsGuardrailVersion", {
      guardrailIdentifier: guardrail.attrGuardrailId,
      description: "Initial version of the EPS Assist Me Guardrail"
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

    // OpenSearch Serverless Collection for EPS Assist
    const osCollection = new ops.CfnCollection(this, "OsCollection", {
      name: "eps-assist-vector-db",
      description: "EPS Assist Vector Store",
      type: "VECTORSEARCH"
    })
    osCollection.addDependency(osEncryptionPolicy)

    // OpenSearch Serverless Security Policy for public access
    new ops.CfnSecurityPolicy(this, "OsNetworkPolicy", {
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

    // ==== Bedrock Execution Role for Knowledge Base ====
    // This role allows Bedrock to access S3 documents, use OpenSearch Serverless, and call the embedding model.
    const bedrockKbRole = new Role(this, "EpsAssistMeBedrockExecutionRole", {
      assumedBy: new ServicePrincipal("bedrock.amazonaws.com"),
      description: "Role for Bedrock Knowledge Base to access S3 and OpenSearch"
    })

    // Allow Bedrock to read/list objects in the docs S3 bucket
    bedrockKbRole.addToPolicy(new PolicyStatement({
      actions: ["s3:GetObject", "s3:ListBucket"],
      resources: [
        kbDocsBucket.bucketArn,
        `${kbDocsBucket.bucketArn}/*`
      ]
    }))

    // Allow Bedrock full access to your OpenSearch Serverless collection and its indexes
    bedrockKbRole.addToPolicy(new PolicyStatement({
      actions: ["aoss:*"],
      resources: [
        osCollection.attrArn,
        `${osCollection.attrArn}/*`,
        "*" // For initial development, broad access
      ]
    }))

    // Allow Bedrock to call the embedding model
    bedrockKbRole.addToPolicy(new PolicyStatement({
      actions: ["bedrock:InvokeModel"],
      resources: [
        `arn:aws:bedrock:${region}::foundation-model/amazon.titan-embed-text-v2:0`
      ]
    }))

    // ==== IAM Role for Lambda: Create OpenSearch Index ====
    // This role allows the Lambda to create and manage indexes in OpenSearch Serverless.
    const createIndexFunctionRole = new iam.Role(this, "CreateIndexFunctionRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      description: "Lambda role for creating OpenSearch index"
    })

    // Attach managed policy for CloudWatch Logs
    createIndexFunctionRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole")
    )

    // Grant the role permissions to manage OpenSearch collections and indexes
    const collectionArn = `arn:aws:aoss:${region}:${account}:collection/*`
    const indexArn = `arn:aws:aoss:${region}:${account}:index/*`

    createIndexFunctionRole.addToPolicy(new iam.PolicyStatement({
      actions: [
        "aoss:APIAccessAll",
        "aoss:CreateCollectionItems",
        "aoss:CreateIndex",
        "aoss:DeleteCollectionItems",
        "aoss:DeleteIndex",
        "aoss:DescribeCollectionItems",
        "aoss:DescribeIndex",
        "aoss:ReadDocument",
        "aoss:UpdateCollectionItems",
        "aoss:UpdateIndex",
        "aoss:WriteDocument"
      ],
      resources: [collectionArn, indexArn]
    }))

    // ==== IAM Managed Policy: OpenSearch Index Permissions for Lambda ====
    const aossIndexPolicy = new iam.ManagedPolicy(this, "CreateIndexFunctionAossPolicy", {
      description: "Allow Lambda to manage OpenSearch Serverless indices",
      statements: [
        new iam.PolicyStatement({
          actions: [
            "aoss:APIAccessAll",
            "aoss:CreateCollectionItems",
            "aoss:CreateIndex",
            "aoss:DeleteCollectionItems",
            "aoss:DeleteIndex",
            "aoss:DescribeCollectionItems",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:UpdateCollectionItems",
            "aoss:UpdateIndex",
            "aoss:WriteDocument"
          ],
          resources: [collectionArn, indexArn]
        })
      ]
    })

    // ==== Lambda Function for Vector Index Creation ====
    // This Lambda uses the role above to create the index when triggered by a Custom Resource.
    const createIndexFunction = new LambdaFunction(this, "CreateIndexFunction", {
      stackName: props.stackName,
      functionName: `${props.stackName}-CreateIndexFunction`,
      packageBasePath: "packages/createIndexFunction",
      entryPoint: "app.py",
      logRetentionInDays,
      logLevel,
      environmentVariables: {"INDEX_NAME": osCollection.attrId},
      additionalPolicies: [aossIndexPolicy]
    })

    // ==== AOSS Access Policy for Lambda & Bedrock ====
    new ops.CfnAccessPolicy(this, "OsAccessPolicy", {
      name: "eps-assist-access-policy",
      type: "data",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: ["collection/*"], Permission: ["aoss:*"]},
          {ResourceType: "index", Resource: ["index/*/*"], Permission: ["aoss:*"]}
        ],
        Principal: [
          `arn:aws:iam::${account}:role/${createIndexFunction.function.role?.roleName}`,
          bedrockKbRole.roleArn,
          `arn:aws:iam::${account}:root`
        ]
      }])
    })

    // ==== Index Creation: Custom Resource Triggers Lambda ====
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
      onUpdate: {
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
        new PolicyStatement({
          actions: ["lambda:InvokeFunction"],
          resources: [createIndexFunction.function.functionArn]
        })
      ])
    })

    // ==== Bedrock Knowledge Base Resource ====
    const kb = new CfnKnowledgeBase(this, "EpsKb", {
      name: "eps-assist-kb",
      description: "EPS Assist Knowledge Base",
      roleArn: bedrockKbRole.roleArn,
      knowledgeBaseConfiguration: {
        type: "VECTOR",
        vectorKnowledgeBaseConfiguration: {
          embeddingModelArn: `arn:aws:bedrock:${region}::foundation-model/amazon.titan-embed-text-v2:0`
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
    kb.node.addDependency(vectorIndex) // Ensure index exists before KB

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

    // ==== Lambda environment variables ====
    const lambdaEnv: {[key: string]: string} = {
      RAG_MODEL_ID: "anthropic.claude-3-sonnet-20240229-v1:0",
      EMBEDDING_MODEL: "amazon.titan-embed-text-v2:0",
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

    // ==== IAM Policy for Lambda to read SSM parameters ====
    const slackLambdaSSMPolicy = new PolicyStatement({
      actions: ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParameterHistory"],
      resources: [
        slackBotTokenParameter.parameterArn,
        slackSigningSecretParameter.parameterArn
      ]
    })

    // ==== Lambda self-invoke policy (needed for Slack Bolt lazy handlers) ====
    const slackLambdaSelfInvokePolicy = new PolicyStatement({
      actions: ["lambda:InvokeFunction"],
      resources: [
        slackBotLambda.function.functionArn
      ]
    })

    // ==== Bedrock model invocation policy ====
    const slackLambdaBedrockModelPolicy = new PolicyStatement({
      actions: ["bedrock:InvokeModel"],
      resources: [`arn:aws:bedrock:${region}::foundation-model/${lambdaEnv.RAG_MODEL_ID}`]
    })

    // ==== Bedrock KB retrieve and retrieveAndGenerate policy ====
    const slackLambdaBedrockKbPolicy = new PolicyStatement({
      actions: ["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
      resources: [`arn:aws:bedrock:${region}:${account}:knowledge-base/${kb.attrKnowledgeBaseId}`]
    })

    // ==== Guardrail policy ====
    const slackLambdaGuardrailPolicy = new PolicyStatement({
      actions: ["bedrock:ApplyGuardrail"],
      resources: [`arn:aws:bedrock:${region}:${account}:guardrail/*`]
    })

    // ==== Attach all policies to SlackBot Lambda role ====
    slackBotLambda.function.addToRolePolicy(slackLambdaSSMPolicy)
    slackBotLambda.function.addToRolePolicy(slackLambdaSelfInvokePolicy)
    slackBotLambda.function.addToRolePolicy(slackLambdaBedrockModelPolicy)
    slackBotLambda.function.addToRolePolicy(slackLambdaBedrockKbPolicy)
    slackBotLambda.function.addToRolePolicy(slackLambdaGuardrailPolicy)

    // ==== API Gateway & Slack Route ====
    const apiGateway = new RestApiGateway(this, "EpsAssistApiGateway", {
      stackName: props.stackName,
      logRetentionInDays,
      enableMutualTls: false,
      trustStoreKey: "unused",
      truststoreVersion: "unused"
    })
    // Add SlackBot Lambda to API Gateway
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
