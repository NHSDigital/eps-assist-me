import {
  App,
  Stack,
  StackProps,
  CfnOutput
} from "aws-cdk-lib"
import {
  CfnGuardrail,
  CfnGuardrailVersion,
  CfnKnowledgeBase,
  CfnDataSource
} from "aws-cdk-lib/aws-bedrock"
import {PolicyStatement} from "aws-cdk-lib/aws-iam"
import * as cdk from "aws-cdk-lib"
import * as iam from "aws-cdk-lib/aws-iam"
import * as ops from "aws-cdk-lib/aws-opensearchserverless"
import * as cr from "aws-cdk-lib/custom-resources"
import {nagSuppressions} from "../nagSuppressions"
import {Apis} from "../resources/Apis"
import {Functions} from "../resources/Functions"
import {Storage} from "../resources/Storage"
import {Secrets} from "../resources/Secrets"
import {OpenSearchResources} from "../resources/OpenSearchResources"

const EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
const VECTOR_INDEX_NAME = "eps-assist-os-index"
const BEDROCK_KB_NAME = "eps-assist-kb"

export interface EpsAssistMeStackProps extends StackProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
}

export class EpsAssistMeStack extends Stack {
  public constructor(scope: App, id: string, props: EpsAssistMeStackProps) {
    super(scope, id, props)

    // Get variables from context
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

    // Create Secrets construct
    const secrets = new Secrets(this, "Secrets", {
      slackBotToken,
      slackSigningSecret
    })

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
    bedrockExecutionRole.addToPolicy(bedrockKBDeleteRolePolicy)

    // Create Storage construct
    const storage = new Storage(this, "Storage", {
      bedrockExecutionRole
    })

    // Create an IAM policy for S3 access
    const s3AccessListPolicy = new PolicyStatement({
      actions: ["s3:ListBucket"],
      resources: [storage.kbDocsBucket.bucket.bucketArn]
    })
    s3AccessListPolicy.addCondition("StringEquals", {"aws:ResourceAccount": account})

    // Create an IAM policy for S3 access
    const s3AccessGetPolicy = new PolicyStatement({
      actions: ["s3:GetObject", "s3:Delete*"],
      resources: [`${storage.kbDocsBucket.bucket.bucketArn}/*`]
    })
    s3AccessGetPolicy.addCondition("StringEquals", {"aws:ResourceAccount": account})

    bedrockExecutionRole.addToPolicy(s3AccessListPolicy)
    bedrockExecutionRole.addToPolicy(s3AccessGetPolicy)

    // Create bedrock Guardrails for the slack bot
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

    // Add a dependency for the guardrail to the bedrock execution role
    const guardrailVersion = new CfnGuardrailVersion(this, "EpsGuardrailVersion", {
      guardrailIdentifier: guardrail.attrGuardrailId,
      description: "v1.0"
    })

    //Define vars for Guardrail ID and version for the Retrieve&Generate API call
    const GUARD_RAIL_ID = guardrail.attrGuardrailId
    const GUARD_RAIL_VERSION = guardrailVersion.attrVersion

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

    // Create OpenSearch Resources
    const openSearchResources = new OpenSearchResources(this, "OpenSearchResources", {
      bedrockExecutionRole,
      createIndexFunctionRole,
      account
    })

    const endpoint = openSearchResources.collection.endpoint

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
          collectionArn: openSearchResources.collection.collection.attrArn,
          fieldMapping: {
            vectorField: "bedrock-knowledge-base-default-vector",
            textField: "AMAZON_BEDROCK_TEXT_CHUNK",
            metadataField: "AMAZON_BEDROCK_METADATA"
          },
          vectorIndexName: VECTOR_INDEX_NAME
        }
      }
    })

    // Create Functions construct
    const functions = new Functions(this, "Functions", {
      stackName: props.stackName,
      version: props.version,
      commitId: props.commitId,
      logRetentionInDays,
      logLevel,
      createIndexFunctionRole,
      slackBotTokenParameter: secrets.slackBotTokenParameter,
      slackSigningSecretParameter: secrets.slackSigningSecretParameter,
      guardrailId: GUARD_RAIL_ID,
      guardrailVersion: GUARD_RAIL_VERSION,
      collectionId: openSearchResources.collection.collection.attrId,
      knowledgeBaseId: bedrockkb.attrKnowledgeBaseId,
      region,
      account,
      slackBotTokenSecret: secrets.slackBotTokenSecret,
      slackBotSigningSecret: secrets.slackBotSigningSecret
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
          functions.functions.createIndex.function.role?.roleArn,
          `arn:aws:iam::${account}:root`
        ]
      }])
    })
    openSearchResources.collection.collection.addDependency(aossAccessPolicy)

    const vectorIndex = new cr.AwsCustomResource(this, "VectorIndex", {
      installLatestAwsSdk: true,
      onCreate: {
        service: "Lambda",
        action: "invoke",
        parameters: {
          FunctionName: functions.functions.createIndex.function.functionName,
          InvocationType: "RequestResponse",
          Payload: JSON.stringify({
            RequestType: "Create",
            CollectionName: openSearchResources.collection.collection.name,
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
          FunctionName: functions.functions.createIndex.function.functionName,
          InvocationType: "RequestResponse",
          Payload: JSON.stringify({
            RequestType: "Delete",
            CollectionName: openSearchResources.collection.collection.name,
            IndexName: VECTOR_INDEX_NAME,
            Endpoint: endpoint
          })
        }
      },
      policy: cr.AwsCustomResourcePolicy.fromStatements([
        new iam.PolicyStatement({
          actions: ["lambda:InvokeFunction"],
          resources: [functions.functions.createIndex.function.functionArn]
        })
      ]),
      timeout: cdk.Duration.seconds(60)
    })

    // Ensure vectorIndex depends on collection
    vectorIndex.node.addDependency(openSearchResources.collection.collection)

    // add a dependency for bedrock kb on the custom resource. Enables vector index to be created before KB
    bedrockkb.node.addDependency(vectorIndex)
    bedrockkb.node.addDependency(functions.functions.createIndex)
    bedrockkb.node.addDependency(openSearchResources.collection.collection)
    bedrockkb.node.addDependency(bedrockExecutionRole)

    // Define a bedrock knowledge base data source with S3 bucket
    const kbDataSource = new CfnDataSource(this, "EpsKbDataSource", {
      name: "eps-assist-kb-ds",
      knowledgeBaseId: bedrockkb.attrKnowledgeBaseId,
      dataSourceConfiguration: {
        type: "S3",
        s3Configuration: {
          bucketArn: storage.kbDocsBucket.bucket.bucketArn
        }
      }
    })

    // Create Apis and pass the Lambda function
    const apis = new Apis(this, "Apis", {
      stackName: props.stackName,
      logRetentionInDays,
      enableMutalTls: false,
      functions: {
        slackBot: functions.functions.slackBot
      }
    })

    // Output: SlackBot Endpoint
    new CfnOutput(this, "SlackBotEndpoint", {
      value: `https://${apis.apis["api"].api.domainName?.domainName}/slack/ask-eps`
    })

    // Final CDK Nag Suppressions
    nagSuppressions(this)
  }
}
