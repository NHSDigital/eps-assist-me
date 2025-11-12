import {
  App,
  Stack,
  StackProps,
  CfnOutput,
  Fn
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
import {DatabaseTables} from "../resources/DatabaseTables"
import {BedrockPromptResources} from "../resources/BedrockPromptResources"
import {S3LambdaNotification} from "../constructs/S3LambdaNotification"
import {VectorIndex} from "../resources/VectorIndex"

export interface EpsAssistMeStackProps extends StackProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
}

export class EpsAssistMeStack extends Stack {
  public constructor(scope: App, id: string, props: EpsAssistMeStackProps) {
    super(scope, id, props)

    // imports
    const mainSlackBotLambdaExecutionRoleArn = Fn.importValue("epsam:lambda:SlackBot:ExecutionRole:Arn")
    // regression testing needs direct lambda invoke — bypasses slack webhooks entirely
    const regressionTestRoleArn = Fn.importValue("regression-test:ExecutionRole:Arn")

    // Get variables from context
    const region = Stack.of(this).region
    const account = Stack.of(this).account
    const logRetentionInDays = Number(this.node.tryGetContext("logRetentionInDays"))
    const logLevel: string = this.node.tryGetContext("logLevel")
    const isPullRequest: boolean = this.node.tryGetContext("isPullRequest")

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
      region
    })

    const vectorIndex = new VectorIndex(this, "VectorIndex", {
      stackName: props.stackName,
      collection: openSearchResources.collection
    })

    // Create VectorKnowledgeBase construct with Bedrock execution role
    const vectorKB = new VectorKnowledgeBaseResources(this, "VectorKB", {
      stackName: props.stackName,
      docsBucket: storage.kbDocsBucket.bucket,
      bedrockExecutionRole: bedrockExecutionRole.role,
      collectionArn: openSearchResources.collection.collectionArn,
      vectorIndexName: vectorIndex.indexName,
      region,
      account
    })

    vectorKB.knowledgeBase.node.addDependency(vectorIndex.cfnIndex)

    // Create runtime policies with resource dependencies
    const runtimePolicies = new RuntimePolicies(this, "RuntimePolicies", {
      region,
      account,
      slackBotTokenParameterName: secrets.slackBotTokenParameter.parameterName,
      slackSigningSecretParameterName: secrets.slackSigningSecretParameter.parameterName,
      slackBotStateTableArn: tables.slackBotStateTable.table.tableArn,
      slackBotStateTableKmsKeyArn: tables.slackBotStateTable.kmsKey.keyArn,
      knowledgeBaseArn: vectorKB.knowledgeBase.attrKnowledgeBaseArn,
      guardrailArn: vectorKB.guardrail.guardrailArn,
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
      guardrailId: vectorKB.guardrail.guardrailId,
      guardrailVersion: vectorKB.guardrail.guardrailVersion,
      collectionId: openSearchResources.collection.collectionId,
      knowledgeBaseId: vectorKB.knowledgeBase.attrKnowledgeBaseId,
      dataSourceId: vectorKB.dataSource.attrDataSourceId,
      region,
      account,
      slackBotTokenSecret: secrets.slackBotTokenSecret,
      slackBotSigningSecret: secrets.slackBotSigningSecret,
      slackBotStateTable: tables.slackBotStateTable.table,
      promptName: bedrockPromptResources.queryReformulationPrompt.promptName,
      isPullRequest: isPullRequest,
      mainSlackBotLambdaExecutionRoleArn: mainSlackBotLambdaExecutionRoleArn,
      regressionTestRoleArn: regressionTestRoleArn
    })

    // Add S3 notification to trigger sync Lambda function
    new S3LambdaNotification(this, "S3LambdaNotification", {
      bucket: storage.kbDocsBucket.bucket,
      lambdaFunction: functions.syncKnowledgeBaseFunction.function
    })

    // Create Apis and pass the Lambda function
    const apis = new Apis(this, "Apis", {
      stackName: props.stackName,
      logRetentionInDays,
      functions: {
        slackBot: functions.slackBotLambda
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

    new CfnOutput(this, "kbDocsBucketArn", {
      value: storage.kbDocsBucket.bucket.bucketArn,
      exportName: `${props.stackName}:kbDocsBucket:Arn`
    })
    new CfnOutput(this, "kbDocsBucketName", {
      value: storage.kbDocsBucket.bucket.bucketName,
      exportName: `${props.stackName}:kbDocsBucket:Name`
    })

    new CfnOutput(this, "SlackBotLambdaRoleArn", {
      value: functions.slackBotLambda.executionRole.roleArn,
      exportName: `${props.stackName}:lambda:SlackBot:ExecutionRole:Arn`
    })

    if (isPullRequest) {
      new CfnOutput(this, "VERSION_NUMBER", {
        value: props.version,
        exportName: `${props.stackName}:local:VERSION-NUMBER`
      })
      new CfnOutput(this, "COMMIT_ID", {
        value: props.commitId,
        exportName: `${props.stackName}:local:COMMIT-ID`
      })
      new CfnOutput(this, "slackBotToken", {
        value: slackBotToken,
        exportName: `${props.stackName}:local:slackBotToken`
      })
      new CfnOutput(this, "slackSigningSecret", {
        value: slackSigningSecret,
        exportName: `${props.stackName}:local:slackSigningSecret`
      })
    }
    // Final CDK Nag Suppressions
    nagSuppressions(this)
  }
}
