import {
  App,
  Stack,
  StackProps,
  CfnOutput
} from "aws-cdk-lib"
import {nagSuppressions} from "../nagSuppressions"
import {Apis} from "../resources/Apis"
import {Functions} from "../resources/Functions"
import {Storage} from "../resources/Storage"
import {Secrets} from "../resources/Secrets"
import {OpenSearchResources} from "../resources/OpenSearchResources"
import {VectorKnowledgeBaseResources} from "../resources/VectorKnowledgeBaseResources"
import {IamResources} from "../resources/IamResources"
import {VectorIndex} from "../resources/VectorIndex"
import {SlackDeduplicationTable} from "../resources/SlackDeduplicationTable"

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
      stackName: props.stackName,
      slackBotToken,
      slackSigningSecret
    })

    // Create Slack deduplication table
    const slackDeduplicationTable = new SlackDeduplicationTable(this, "SlackDeduplicationTable", {
      stackName: props.stackName
    })

    // Create Storage construct without Bedrock execution role to avoid circular dependency:
    // - Storage needs to exist first so IamResources can reference the S3 bucket for policies
    // - IamResources creates the Bedrock role that needs S3 access permissions
    // - KMS permissions are added manually after both constructs exist
    const storage = new Storage(this, "Storage", {
      stackName: props.stackName
    })

    // Create IAM Resources
    const iamResources = new IamResources(this, "IamResources", {
      region,
      account,
      kbDocsBucket: storage.kbDocsBucket.bucket,
      slackBotTokenParameterName: secrets.slackBotTokenParameter.parameterName,
      slackSigningSecretParameterName: secrets.slackSigningSecretParameter.parameterName
    })

    // Create OpenSearch Resources
    const openSearchResources = new OpenSearchResources(this, "OpenSearchResources", {
      stackName: props.stackName,
      bedrockExecutionRole: iamResources.bedrockExecutionRole,
      account
    })

    const endpoint = openSearchResources.collection.endpoint

    // Create Functions construct without vector KB dependencies
    const functions = new Functions(this, "Functions", {
      stackName: props.stackName,
      version: props.version,
      commitId: props.commitId,
      logRetentionInDays,
      logLevel,
      createIndexManagedPolicy: iamResources.createIndexManagedPolicy,
      slackBotManagedPolicy: iamResources.slackBotManagedPolicy,
      slackBotTokenParameter: secrets.slackBotTokenParameter,
      slackSigningSecretParameter: secrets.slackSigningSecretParameter,
      guardrailId: "", // Will be set after vector KB is created
      guardrailVersion: "", // Will be set after vector KB is created
      collectionId: openSearchResources.collection.collection.attrId,
      knowledgeBaseId: "", // Will be set after vector KB is created
      region,
      account,
      slackBotTokenSecret: secrets.slackBotTokenSecret,
      slackBotSigningSecret: secrets.slackBotSigningSecret,
      slackDeduplicationTable: slackDeduplicationTable.table
    })

    // Create vector index
    const vectorIndex = new VectorIndex(this, "VectorIndex", {
      indexName: VECTOR_INDEX_NAME,
      collection: openSearchResources.collection.collection,
      createIndexFunction: functions.functions.createIndex,
      endpoint
    })

    // Create VectorKnowledgeBase construct after vector index
    const vectorKB = new VectorKnowledgeBaseResources(this, "VectorKB", {
      stackName: props.stackName,
      docsBucket: storage.kbDocsBucket.bucket,
      bedrockExecutionRole: iamResources.bedrockExecutionRole,
      collectionArn: `arn:aws:aoss:${region}:${account}:collection/${openSearchResources.collection.collection.attrId}`,
      vectorIndexName: VECTOR_INDEX_NAME
    })

    // Ensure knowledge base waits for vector index
    vectorKB.knowledgeBase.node.addDependency(vectorIndex.vectorIndex)

    // Update SlackBot Lambda environment variables with vector KB info
    functions.functions.slackBot.function.addEnvironment("GUARD_RAIL_ID", vectorKB.guardrail.attrGuardrailId)
    functions.functions.slackBot.function.addEnvironment("GUARD_RAIL_VERSION", vectorKB.guardrail.attrVersion)
    functions.functions.slackBot.function.addEnvironment("KNOWLEDGEBASE_ID", vectorKB.knowledgeBase.attrKnowledgeBaseId)

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
    new CfnOutput(this, "SlackBotEventsEndpoint", {
      value: `https://${apis.apis["api"].api.domainName?.domainName}/slack/events`,
      description: "Slack Events API endpoint for @mentions and direct messages"
    })

    // Final CDK Nag Suppressions
    nagSuppressions(this)
  }
}
