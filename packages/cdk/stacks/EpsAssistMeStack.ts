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
import {BedrockExecutionRole} from "../resources/BedrockExecutionRole"
import {RuntimePolicies} from "../resources/RuntimePolicies"
import {VectorIndex} from "../resources/VectorIndex"
import {DatabaseTables} from "../resources/DatabaseTables"
import {BedrockPromptResources} from "../resources/BedrockPromptResources"
import {S3LambdaNotification} from "../constructs/S3LambdaNotification"

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

    // Create DatabaseTables
    const tables = new DatabaseTables(this, "DatabaseTables", {
      stackName: props.stackName
    })

    // Create Bedrock Prompt Resources
    const bedrockPromptResources = new BedrockPromptResources(this, "BedrockPromptResources", {
      stackName: props.stackName
    })

    // Create Storage construct first as it has no dependencies
    const storage = new Storage(this, "Storage", {
      stackName: props.stackName
    })

    // Create Bedrock execution role without dependencies
    const bedrockExecutionRole = new BedrockExecutionRole(this, "BedrockExecutionRole", {
      region,
      account,
      kbDocsBucket: storage.kbDocsBucket.bucket
    })

    // Create OpenSearch Resources with Bedrock execution role
    const openSearchResources = new OpenSearchResources(this, "OpenSearchResources", {
      stackName: props.stackName,
      bedrockExecutionRole: bedrockExecutionRole.role,
      account,
      region
    })

    const endpoint = openSearchResources.collection.endpoint

    // Create VectorKnowledgeBase construct with Bedrock execution role
    const vectorKB = new VectorKnowledgeBaseResources(this, "VectorKB", {
      stackName: props.stackName,
      docsBucket: storage.kbDocsBucket.bucket,
      bedrockExecutionRole: bedrockExecutionRole.role,
      collectionArn: openSearchResources.collection.collectionArn,
      vectorIndexName: VECTOR_INDEX_NAME,
      region,
      account
    })

    // Create runtime policies with resource dependencies
    const runtimePolicies = new RuntimePolicies(this, "RuntimePolicies", {
      region,
      account,
      slackBotTokenParameterName: secrets.slackBotTokenParameter.parameterName,
      slackSigningSecretParameterName: secrets.slackSigningSecretParameter.parameterName,
      slackBotStateTableArn: tables.slackBotStateTable.table.tableArn,
      slackBotStateTableKmsKeyArn: tables.slackBotStateTable.kmsKey.keyArn,
      knowledgeBaseArn: vectorKB.knowledgeBase.attrKnowledgeBaseArn,
      guardrailArn: vectorKB.guardrail.attrGuardrailArn,
      dataSourceArn: vectorKB.dataSourceArn,
      promptName: bedrockPromptResources.queryReformulationPrompt.promptName
    })

    // Create Functions construct with actual values from VectorKB
    const functions = new Functions(this, "Functions", {
      stackName: props.stackName,
      version: props.version,
      commitId: props.commitId,
      logRetentionInDays,
      logLevel,
      createIndexManagedPolicy: runtimePolicies.createIndexPolicy,
      slackBotManagedPolicy: runtimePolicies.slackBotPolicy,
      syncKnowledgeBaseManagedPolicy: runtimePolicies.syncKnowledgeBasePolicy,
      slackBotTokenParameter: secrets.slackBotTokenParameter,
      slackSigningSecretParameter: secrets.slackSigningSecretParameter,
      guardrailId: vectorKB.guardrail.attrGuardrailId,
      guardrailVersion: vectorKB.guardrail.attrVersion,
      collectionId: openSearchResources.collection.collection.attrId,
      knowledgeBaseId: vectorKB.knowledgeBase.attrKnowledgeBaseId,
      dataSourceId: vectorKB.dataSource.attrDataSourceId,
      region,
      account,
      slackBotTokenSecret: secrets.slackBotTokenSecret,
      slackBotSigningSecret: secrets.slackBotSigningSecret,
      slackBotStateTable: tables.slackBotStateTable.table,
      feedbackTable: tables.feedbackTable.table,
      promptName: bedrockPromptResources.queryReformulationPrompt.promptName
    })

    // Create vector index after Functions are created
    const vectorIndex = new VectorIndex(this, "VectorIndex", {
      indexName: VECTOR_INDEX_NAME,
      collection: openSearchResources.collection.collection,
      endpoint
    })

    // Ensure knowledge base waits for vector index
    vectorKB.knowledgeBase.node.addDependency(vectorIndex.cfnIndex)

    // Add S3 notification to trigger sync Lambda function
    new S3LambdaNotification(this, "S3LambdaNotification", {
      bucket: storage.kbDocsBucket.bucket,
      lambdaFunction: functions.functions.syncKnowledgeBase.function
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
    new CfnOutput(this, "SlackBotEventsEndpoint", {
      value: `https://${apis.apis["api"].api.domainName?.domainName}/slack/events`,
      description: "Slack Events API endpoint for @mentions and direct messages"
    })

    // Output: Bedrock Prompt ARN
    new CfnOutput(this, "QueryReformulationPromptArn", {
      value: bedrockPromptResources.queryReformulationPrompt.promptArn,
      description: "ARN of the query reformulation prompt in Bedrock"
    })

    // Final CDK Nag Suppressions
    nagSuppressions(this)
  }
}
