import {
  App,
  Stack,
  StackProps,
  CfnOutput,
  Duration
} from "aws-cdk-lib"
import {PolicyStatement, Effect, ArnPrincipal} from "aws-cdk-lib/aws-iam"
import {CfnAccessPolicy} from "aws-cdk-lib/aws-opensearchserverless"
import {nagSuppressions} from "../nagSuppressions"
import {Apis} from "../resources/Apis"
import {Functions} from "../resources/Functions"
import {Storage} from "../resources/Storage"
import {Secrets} from "../resources/Secrets"
import {OpenSearchResources} from "../resources/OpenSearchResources"
import {VectorKnowledgeBaseResources} from "../resources/VectorKnowledgeBaseResources"
import {IamResources} from "../resources/IamResources"
import {VectorIndex} from "../resources/VectorIndex"

const VECTOR_INDEX_NAME = "eps-assist-os-index"

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
    const logRetentionInDays = Number(this.node.tryGetContext("logRetentionInDays"))
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

    // Create Storage construct without Bedrock execution role to avoid circular dependency:
    // - Storage needs to exist first so IamResources can reference the S3 bucket for policies
    // - IamResources creates the Bedrock role that needs S3 access permissions
    // - KMS permissions are added manually after both constructs exist
    const storage = new Storage(this, "Storage")

    // Create IAM Resources
    const iamResources = new IamResources(this, "IamResources", {
      region,
      account,
      kbDocsBucket: storage.kbDocsBucket.bucket
    })

    // Update storage with bedrock role for KMS access
    if (storage.kbDocsBucket.kmsKey) {
      storage.kbDocsBucket.kmsKey.addToResourcePolicy(new PolicyStatement({
        effect: Effect.ALLOW,
        principals: [new ArnPrincipal(iamResources.bedrockExecutionRole.roleArn)],
        actions: ["kms:Decrypt", "kms:DescribeKey"],
        resources: ["*"]
      }))
    }

    // Create OpenSearch Resources
    const openSearchResources = new OpenSearchResources(this, "OpenSearchResources", {
      bedrockExecutionRole: iamResources.bedrockExecutionRole,
      createIndexFunctionRole: iamResources.createIndexFunctionRole,
      account
    })

    const endpoint = openSearchResources.collection.endpoint

    // Create VectorKnowledgeBase construct
    const vectorKB = new VectorKnowledgeBaseResources(this, "VectorKB", {
      docsBucket: storage.kbDocsBucket.bucket,
      bedrockExecutionRole: iamResources.bedrockExecutionRole,
      collectionArn: `arn:aws:aoss:${region}:${account}:collection/${openSearchResources.collection.collection.attrId}`,
      vectorIndexName: VECTOR_INDEX_NAME
    })

    // Create Functions construct
    const functions = new Functions(this, "Functions", {
      stackName: props.stackName,
      version: props.version,
      commitId: props.commitId,
      logRetentionInDays,
      logLevel,
      createIndexFunctionRole: iamResources.createIndexFunctionRole,
      slackBotTokenParameter: secrets.slackBotTokenParameter,
      slackSigningSecretParameter: secrets.slackSigningSecretParameter,
      guardrailId: vectorKB.guardrail.attrGuardrailId,
      guardrailVersion: vectorKB.guardrail.attrVersion,
      collectionId: openSearchResources.collection.collection.attrId,
      knowledgeBaseId: vectorKB.knowledgeBase.attrKnowledgeBaseId,
      region,
      account,
      slackBotTokenSecret: secrets.slackBotTokenSecret,
      slackBotSigningSecret: secrets.slackBotSigningSecret
    })

    // Define OpenSearchServerless access policy to access the index and collection
    // from the Amazon Bedrock execution role and the lambda execution role
    const aossAccessPolicy = new CfnAccessPolicy(this, "aossAccessPolicy", {
      name: "eps-assist-access-policy",
      type: "data",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: ["collection/*"], Permission: ["aoss:*"]},
          {ResourceType: "index", Resource: ["index/*/*"], Permission: ["aoss:*"]}
        ],
        // Add principal of bedrock execution role and lambda execution role
        Principal: [
          iamResources.bedrockExecutionRole.roleArn,
          functions.functions.createIndex.function.role?.roleArn,
          `arn:aws:iam::${account}:root`
        ]
      }])
    })
    openSearchResources.collection.collection.addDependency(aossAccessPolicy)

    // Create vector index
    const vectorIndex = new VectorIndex(this, "VectorIndex", {
      indexName: VECTOR_INDEX_NAME,
      collection: openSearchResources.collection.collection,
      createIndexFunction: functions.functions.createIndex,
      endpoint
    })

    // add a dependency for bedrock kb on the custom resource. Enables vector index to be created before KB
    vectorKB.knowledgeBase.node.addDependency(vectorIndex.vectorIndex)
    vectorKB.knowledgeBase.node.addDependency(functions.functions.createIndex)
    vectorKB.knowledgeBase.node.addDependency(openSearchResources.collection.collection)
    vectorKB.knowledgeBase.node.addDependency(iamResources.bedrockExecutionRole)

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
