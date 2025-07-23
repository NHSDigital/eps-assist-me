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
import {
  CfnGuardrail,
  CfnGuardrailVersion,
  CfnKnowledgeBase,
  CfnDataSource
} from "aws-cdk-lib/aws-bedrock"
import {RestApiGateway} from "../constructs/RestApiGateway"
import {LambdaFunction} from "../constructs/LambdaFunction"
import {LambdaEndpoint} from "../constructs/RestApiGateway/LambdaEndpoint"
import {HttpMethod} from "aws-cdk-lib/aws-lambda"
import {PolicyStatement} from "aws-cdk-lib/aws-iam"
import * as cdk from "aws-cdk-lib"
import * as iam from "aws-cdk-lib/aws-iam"
import * as ops from "aws-cdk-lib/aws-opensearchserverless"
import * as cr from "aws-cdk-lib/custom-resources"
import * as ssm from "aws-cdk-lib/aws-ssm"
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager"
import {nagSuppressions} from "../nagSuppressions"

const RAG_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
const EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
const SLACK_SLASH_COMMAND = "/ask-eps"
const COLLECTION_NAME = "eps-assist-vector-db"
const VECTOR_INDEX_NAME = "eps-assist-os-index"
const BEDROCK_KB_NAME = "eps-assist-kb"
const BEDROCK_KB_DATA_SOURCE = "eps-assist-kb-ds"
const LAMBDA_MEMORY_SIZE = "265"

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

    // Get secrets from context or fail if not provided
    const slackBotToken: string = this.node.tryGetContext("slackBotToken")
    const slackSigningSecret: string = this.node.tryGetContext("slackSigningSecret")

    if (!slackBotToken || !slackSigningSecret) {
      throw new Error("Missing required context variables. Please provide slackBotToken and slackSigningSecret")
    }

    // Create secrets in Secrets Manager
    const slackBotTokenSecret = new secretsmanager.Secret(this, "SlackBotTokenSecret", {
      secretName: "/eps-assist/slack/bot-token",
      description: "Slack Bot OAuth Token for EPS Assist",
      secretStringValue: cdk.SecretValue.unsafePlainText(JSON.stringify({
        token: slackBotToken
      }))
    })

    const slackBotSigningSecret = new secretsmanager.Secret(this, "SlackBotSigningSecret", {
      secretName: "/eps-assist/slack/signing-secret",
      description: "Slack Signing Secret",
      secretStringValue: cdk.SecretValue.unsafePlainText(JSON.stringify({
        secret: slackSigningSecret
      }))
    })

    // Create SSM parameters that reference the secrets
    const slackBotTokenParameter = new ssm.StringParameter(this, "SlackBotTokenParameter", {
      parameterName: "/eps-assist/slack/bot-token/parameter",
      stringValue: `{{resolve:secretsmanager:${slackBotTokenSecret.secretName}}}`,
      description: "Reference to Slack Bot Token in Secrets Manager",
      tier: ssm.ParameterTier.STANDARD
    })

    const slackSigningSecretParameter = new ssm.StringParameter(this, "SlackSigningSecretParameter", {
      parameterName: "/eps-assist/slack/signing-secret/parameter",
      stringValue: `{{resolve:secretsmanager:${slackBotSigningSecret.secretName}}}`,
      description: "Reference to Slack Signing Secret in Secrets Manager",
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
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      enforceSSL: true,
      versioned: false,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED
    })

    const kbDocsBucket = new Bucket(this, "EpsAssistDocsBucket", {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryptionKey: cloudWatchLogsKmsKey,
      encryption: BucketEncryption.KMS,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      enforceSSL: true,
      versioned: true,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED,
      serverAccessLogsBucket: accessLogBucket,
      serverAccessLogsPrefix: "s3-access-logs/"
    })

    // ==== IAM Policies for S3 access (Bedrock Execution Role) ====
    const s3AccessListPolicy = new PolicyStatement({
      actions: ["s3:ListBucket"],
      resources: [kbDocsBucket.bucketArn]
    })
    s3AccessListPolicy.addCondition("StringEquals", {"aws:ResourceAccount": account})

    const s3AccessGetPolicy = new PolicyStatement({
      actions: ["s3:GetObject", "s3:Delete*"],
      resources: [`${kbDocsBucket.bucketArn}/*`]
    })
    s3AccessGetPolicy.addCondition("StringEquals", {"aws:ResourceAccount": account})

    // Create an IAM policy to invoke Bedrock models and access titan v1 embedding model
    const bedrockExecutionRolePolicy = new PolicyStatement()
    bedrockExecutionRolePolicy.addActions("bedrock:InvokeModel")
    bedrockExecutionRolePolicy.addResources(`arn:aws:bedrock:${region}::foundation-model/${EMBEDDING_MODEL}`)

    // Create an IAM policy to delete Bedrock knowledgebase
    const bedrockKBDeleteRolePolicy = new PolicyStatement()
    bedrockKBDeleteRolePolicy.addActions("bedrock:Delete*")
    bedrockKBDeleteRolePolicy.addResources(`arn:aws:bedrock:${region}:${account}:knowledge-base/*`)

    // Create IAM policy to call OpensearchServerless
    const bedrockOSSPolicyForKnowledgeBase = new PolicyStatement()
    bedrockOSSPolicyForKnowledgeBase.addActions("aoss:APIAccessAll")
    bedrockOSSPolicyForKnowledgeBase.addActions(
      "aoss:DeleteAccessPolicy",
      "aoss:DeleteCollection",
      "aoss:DeleteLifecyclePolicy",
      "aoss:DeleteSecurityConfig",
      "aoss:DeleteSecurityPolicy"
    )
    bedrockOSSPolicyForKnowledgeBase.addResources(`arn:aws:aoss:${region}:${account}:collection/*`)

    // Define IAM Role and add Iam policies for bedrock execution role
    const bedrockExecutionRole = new iam.Role(this, "EpsAssistMeBedrockExecutionRole", {
      assumedBy: new iam.ServicePrincipal("bedrock.amazonaws.com"),
      description: "Role for Bedrock Knowledge Base to access S3 and OpenSearch"
    })
    bedrockExecutionRole.addToPolicy(bedrockExecutionRolePolicy)
    bedrockExecutionRole.addToPolicy(bedrockOSSPolicyForKnowledgeBase)
    bedrockExecutionRole.addToPolicy(s3AccessListPolicy)
    bedrockExecutionRole.addToPolicy(s3AccessGetPolicy)
    bedrockExecutionRole.addToPolicy(bedrockKBDeleteRolePolicy)

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
      description: "v1.0"
    })

    //Define vars for Guardrail ID and version for the Retrieve&Generate API call
    const GUARD_RAIL_ID = guardrail.attrGuardrailId
    const GUARD_RAIL_VERSION = guardrailVersion.attrVersion

    //Define OpenSearchServerless Collection & depends on policies
    const osCollection = new ops.CfnCollection(this, "osCollection", {
      name: COLLECTION_NAME,
      description: "EPS Assist Vector Store",
      type: "VECTORSEARCH"
    })

    // Define AOSS vector DB encryption policy with AWSOwned key true
    const aossEncryptionPolicy = new ops.CfnSecurityPolicy(this, "aossEncryptionPolicy", {
      name: "eps-assist-encryption-policy",
      type: "encryption",
      policy: JSON.stringify({
        Rules: [{ResourceType: "collection", Resource: ["collection/eps-assist-vector-db"]}],
        AWSOwnedKey: true
      })
    })
    osCollection.addDependency(aossEncryptionPolicy)

    // Define Vector DB network policy with AllowFromPublic true. include collection & dashboard
    const aossNetworkPolicy = new ops.CfnSecurityPolicy(this, "aossNetworkPolicy", {
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
    osCollection.addDependency(aossNetworkPolicy)

    // Define createIndexFunction execution role and policy. Managed role 'AWSLambdaBasicExecutionRole'
    const createIndexFunctionRole = new iam.Role(this, "CreateIndexFunctionRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      description: "Lambda role for creating OpenSearch index"
    })

    createIndexFunctionRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole")
    )
    createIndexFunctionRole.addToPolicy(new PolicyStatement({
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
      ],
      effect: iam.Effect.ALLOW
    }))

    // Define a lambda function to create an opensearch serverless index
    const createIndexFunction = new LambdaFunction(this, "CreateIndexFunction", {
      stackName: props.stackName,
      functionName: `${props.stackName}-CreateIndexFunction`,
      packageBasePath: "packages/createIndexFunction",
      entryPoint: "app.py",
      logRetentionInDays,
      logLevel,
      environmentVariables: {"INDEX_NAME": osCollection.attrId},
      additionalPolicies: [],
      role: createIndexFunctionRole
    })

    // Define OpenSearchServerless access policy to access the index and collection
    // from the Amazon Bedrock execution role and the lambda execution role
    const aossAccessPolicy = new ops.CfnAccessPolicy(this, "aossAccessPolicy", {
      name: "eps-assist-access-policy",
      type: "data",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: ["collection/*"], Permission: ["aoss:*"]},
          {ResourceType: "index", Resource: ["index/*/*"], Permission: ["aoss:*"]}
        ],
        // Add principal of bedrock execution role and lambda execution role
        Principal: [
          bedrockExecutionRole.roleArn,
          createIndexFunction.function.role?.roleArn,
          `arn:aws:iam::${account}:root`
        ]
      }])
    })
    //this.serverlessCollection = osCollection;
    osCollection.addDependency(aossAccessPolicy)

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
            IndexName: VECTOR_INDEX_NAME,
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
            IndexName: VECTOR_INDEX_NAME,
            Endpoint: endpoint
          })
        }
        //physicalResourceId: cr.PhysicalResourceId.of('vectorIndexResource'),
      },
      policy: cr.AwsCustomResourcePolicy.fromStatements([
        new iam.PolicyStatement({
          actions: ["lambda:InvokeFunction"],
          resources: [createIndexFunction.function.functionArn]
        })
      ]),
      timeout: cdk.Duration.seconds(60)
    })

    // Ensure vectorIndex depends on collection
    vectorIndex.node.addDependency(osCollection)

    // Define a Bedrock knowledge base with type opensearch serverless and titan for embedding model
    const bedrockkb = new CfnKnowledgeBase(this, "EpsKb", {
      name: BEDROCK_KB_NAME,
      description: "EPS Assist Knowledge Base",
      roleArn: bedrockExecutionRole.roleArn,
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
          fieldMapping: {
            vectorField: "bedrock-knowledge-base-default-vector",
            textField: "AMAZON_BEDROCK_TEXT_CHUNK",
            metadataField: "AMAZON_BEDROCK_METADATA"
          },
          vectorIndexName: VECTOR_INDEX_NAME
        }
      }
    })
    // add a dependency for bedrock kb on the custom resource. Enables vector index to be created before KB
    bedrockkb.node.addDependency(vectorIndex)
    bedrockkb.node.addDependency(createIndexFunction)
    bedrockkb.node.addDependency(osCollection)
    bedrockkb.node.addDependency(bedrockExecutionRole)

    // Define a bedrock knowledge base data source with S3 bucket
    const kbDataSource = new CfnDataSource(this, "EpsKbDataSource", {
      name: "eps-assist-kb-ds",
      knowledgeBaseId: bedrockkb.attrKnowledgeBaseId,
      dataSourceConfiguration: {
        type: "S3",
        s3Configuration: {
          bucketArn: kbDocsBucket.bucketArn
        }
      }
    })

    // Create an IAM policy to allow the lambda to invoke models in Amazon Bedrock
    const lambdaBedrockModelPolicy = new PolicyStatement()
    lambdaBedrockModelPolicy.addActions("bedrock:InvokeModel")
    lambdaBedrockModelPolicy.addResources(`arn:aws:bedrock:${region}::foundation-model/${RAG_MODEL_ID}`)

    // Create an IAM policy to allow the lambda to call Retrieve and Retrieve and Generate on a Bedrock Knowledge Base
    const lambdaBedrockKbPolicy = new PolicyStatement()
    lambdaBedrockKbPolicy.addActions("bedrock:Retrieve")
    lambdaBedrockKbPolicy.addActions("bedrock:RetrieveAndGenerate")
    lambdaBedrockKbPolicy.addResources(
      `arn:aws:bedrock:${region}:${account}:knowledge-base/${bedrockkb.attrKnowledgeBaseId}`
    )

    // Create an IAM policy to allow the lambda to call SSM
    const lambdaSSMPolicy = new PolicyStatement()
    lambdaSSMPolicy.addActions("ssm:GetParameter")
    //lambdaSSMPolicy.addActions("ssm:GetParameters");
    // lambdaSSMPolicy.addResources("slackBotTokenParameter.parameterArn");
    // lambdaSSMPolicy.addResources("slackBotSigningSecret.parameterArn");
    lambdaSSMPolicy.addResources(
      `arn:aws:ssm:${region}:${account}:parameter${slackBotTokenParameter.parameterName}`)
    lambdaSSMPolicy.addResources(
      `arn:aws:ssm:${region}:${account}:parameter${slackSigningSecretParameter.parameterName}`)

    //arn:aws:ssm:us-east-1:859498851685:parameter/slack/bot-token/parameter
    //"arn:aws:ssm:us-east-2:123456789012:parameter/prod-*"
    //(`arn:aws:bedrock:${region}:${account}:knowledge-base/${bedrockkb.attrKnowledgeBaseId}`);

    const lambdaReinvokePolicy = new PolicyStatement()
    lambdaReinvokePolicy.addActions("lambda:InvokeFunction")
    lambdaReinvokePolicy.addResources(
      `arn:aws:lambda:${region}:${account}:function:${slackBotLambda.function.functionName}`,
      `arn:aws:lambda:${region}:${account}:function:AmazonBedrock*`
    )
    slackBotLambda.function.addToRolePolicy(lambdaReinvokePolicy)

    const lambdaGRinvokePolicy = new PolicyStatement()
    lambdaGRinvokePolicy.addActions("bedrock:ApplyGuardrail")
    lambdaGRinvokePolicy.addResources(`arn:aws:bedrock:${region}:${account}:guardrail/*`)

    // Create the SlackBot (slash command) integration to Amazon Bedrock Knowledge base responses.
    const slackBotLambda = new LambdaFunction(this, "SlackBotLambda", {
      stackName: props.stackName,
      functionName: `${props.stackName}-SlackBotFunction`,
      packageBasePath: "packages/slackBotFunction",
      entryPoint: "app.py",
      logRetentionInDays,
      logLevel,
      additionalPolicies: [],
      environmentVariables: {
        "RAG_MODEL_ID": RAG_MODEL_ID,
        "SLACK_SLASH_COMMAND": SLACK_SLASH_COMMAND,
        "KNOWLEDGEBASE_ID": bedrockkb.attrKnowledgeBaseId,
        "BEDROCK_KB_DATA_SOURCE": BEDROCK_KB_DATA_SOURCE,
        "LAMBDA_MEMORY_SIZE": LAMBDA_MEMORY_SIZE,
        // "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
        // "SLACK_SIGNING_SECRET": SLACK_SIGNING_SECRET,
        "SLACK_BOT_TOKEN_PARAMETER": slackBotTokenParameter.parameterName,
        "SLACK_SIGNING_SECRET_PARAMETER": slackSigningSecretParameter.parameterName,
        "GUARD_RAIL_ID": GUARD_RAIL_ID,
        "GUARD_RAIL_VERSION": GUARD_RAIL_VERSION
      }
    })

    // Grant the Lambda function permission to read the secrets
    slackBotTokenSecret.grantRead(slackBotLambda.function)
    slackBotSigningSecret.grantRead(slackBotLambda.function)

    // Attach listed IAM policies to the Lambda functions Execution role
    slackBotLambda.function.addToRolePolicy(lambdaBedrockModelPolicy)
    slackBotLambda.function.addToRolePolicy(lambdaBedrockKbPolicy)
    slackBotLambda.function.addToRolePolicy(lambdaReinvokePolicy)
    slackBotLambda.function.addToRolePolicy(lambdaGRinvokePolicy)
    slackBotLambda.function.addToRolePolicy(lambdaSSMPolicy)

    // Define the API Gateway and connect the '/slack/ask-eps' POST endpoint to the SlackBot Lambda function
    const apiGateway = new RestApiGateway(this, "EpsAssistApiGateway", {
      stackName: props.stackName,
      logRetentionInDays,
      enableMutualTls: false,
      trustStoreKey: "unused",
      truststoreVersion: "unused"
    })

    const slackResource = apiGateway.api.root.addResource("slack")

    // Create the '/slack/ask-eps' POST endpoint and integrate it with the SlackBot Lambda
    new LambdaEndpoint(this, "SlackAskEpsEndpoint", {
      parentResource: slackResource,
      resourceName: "ask-eps",
      method: HttpMethod.POST,
      restApiGatewayRole: apiGateway.role,
      lambdaFunction: slackBotLambda
    })

    // ==== Output: SlackBot Endpoint ====
    new CfnOutput(this, "SlackBotEndpoint", {
      value: `https://${apiGateway.api.domainName?.domainName}/slack/ask-eps`
    })

    // ==== Final CDK Nag Suppressions ====
    nagSuppressions(this)
  }
}
