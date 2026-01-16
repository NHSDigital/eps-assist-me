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
import {ManagedPolicy, PolicyStatement, Role} from "aws-cdk-lib/aws-iam"
import {BedrockPromptSettings} from "../resources/BedrockPromptSettings"
import {BedrockLoggingConfiguration} from "../resources/BedrockLoggingConfiguration"
import {Bucket} from "aws-cdk-lib/aws-s3"

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
    const deploymentRoleImport = Fn.importValue("ci-resources:CloudFormationDeployRole")
    // regression testing needs direct lambda invoke — bypasses slack webhooks entirely
    const regressionTestRoleArn = Fn.importValue("ci-resources:AssistMeRegressionTestRole")
    const auditLoggingBucketImport = Fn.importValue("account-resources:AuditLoggingBucket")

    // Get variables from context
    const region = Stack.of(this).region
    const account = Stack.of(this).account
    const cdkExecRoleArn = `arn:aws:iam::${account}:role/cdk-hnb659fds-cfn-exec-role-${account}-${region}`

    const logRetentionInDays = Number(this.node.tryGetContext("logRetentionInDays"))
    const logLevel: string = this.node.tryGetContext("logLevel")
    const isPullRequest: boolean = this.node.tryGetContext("isPullRequest")
    const runRegressionTests: boolean = this.node.tryGetContext("runRegressionTests")
    const enableBedrockLogging: boolean = this.node.tryGetContext("enableBedrockLogging") === "true"

    // Get secrets from context or fail if not provided
    const slackBotToken: string = this.node.tryGetContext("slackBotToken")
    const slackSigningSecret: string = this.node.tryGetContext("slackSigningSecret")

    const cdkExecRole = Role.fromRoleArn(this, "CdkExecRole", cdkExecRoleArn)
    const deploymentRole = Role.fromRoleArn(this, "deploymentRole", deploymentRoleImport)
    const auditLoggingBucket = Bucket.fromBucketArn(
      this, "AuditLoggingBucket", auditLoggingBucketImport)

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

    // Create Bedrock Prompt Collection
    const bedrockPromptCollection = new BedrockPromptSettings(this, "BedrockPromptCollection")

    // Create Bedrock Prompt Resources
    const bedrockPromptResources = new BedrockPromptResources(this, "BedrockPromptResources", {
      stackName: props.stackName,
      settings: bedrockPromptCollection
    })

    // Create Storage construct first as it has no dependencies
    const storage = new Storage(this, "Storage", {
      stackName: props.stackName,
      deploymentRole: deploymentRole,
      auditLoggingBucket: auditLoggingBucket
    })

    // Create Bedrock execution role without dependencies
    const bedrockExecutionRole = new BedrockExecutionRole(this, "BedrockExecutionRole", {
      region,
      account,
      kbDocsBucket: storage.kbDocsBucket,
      kbDocsKmsKey: storage.kbDocsKmsKey
    })

    // Create OpenSearch Resources with Bedrock execution role
    const openSearchResources = new OpenSearchResources(this, "OpenSearchResources", {
      stackName: props.stackName,
      bedrockExecutionRole: bedrockExecutionRole.role,
      cdkExecutionRole: cdkExecRole,
      region
    })

    const vectorIndex = new VectorIndex(this, "VectorIndex", {
      stackName: props.stackName,
      collection: openSearchResources.collection
    })

    // This dependency ensures the OpenSearch access policy is created before the VectorIndex
    // and deleted after the VectorIndex is deleted to prevent deletion or deployment failures
    vectorIndex.node.addDependency(openSearchResources.deploymentPolicy)

    // Create Bedrock logging configuration for model invocations
    const bedrockLogging = new BedrockLoggingConfiguration(this, "BedrockLogging", {
      stackName: props.stackName,
      region,
      account,
      logRetentionInDays,
      enableLogging: enableBedrockLogging
    })

    // Create VectorKnowledgeBase construct with Bedrock execution role
    const vectorKB = new VectorKnowledgeBaseResources(this, "VectorKB", {
      stackName: props.stackName,
      docsBucket: storage.kbDocsBucket,
      bedrockExecutionRole: bedrockExecutionRole.role,
      collectionArn: openSearchResources.collection.collectionArn,
      vectorIndexName: vectorIndex.indexName,
      region,
      account,
      logRetentionInDays
    })

    vectorKB.knowledgeBase.node.addDependency(vectorIndex.indexReadyWait.customResource)

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
      promptName: bedrockPromptResources.queryReformulationPrompt.promptName,
      ragModelId: bedrockPromptResources.ragModelId,
      queryReformulationModelId: bedrockPromptResources.queryReformulationModelId
    })

    // Create Functions construct with actual values from VectorKB
    const functions = new Functions(this, "Functions", {
      stackName: props.stackName,
      version: props.version,
      commitId: props.commitId,
      logRetentionInDays,
      logLevel,
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
      reformulationPromptName: bedrockPromptResources.queryReformulationPrompt.promptName,
      ragResponsePromptName: bedrockPromptResources.ragResponsePrompt.promptName,
      reformulationPromptVersion: bedrockPromptResources.queryReformulationPrompt.promptVersion,
      ragResponsePromptVersion: bedrockPromptResources.ragResponsePrompt.promptVersion,
      ragModelId: bedrockPromptResources.ragModelId,
      queryReformulationModelId: bedrockPromptResources.queryReformulationModelId,
      isPullRequest: isPullRequest,
      mainSlackBotLambdaExecutionRoleArn: mainSlackBotLambdaExecutionRoleArn
    })

    // Add S3 notification to trigger sync Lambda function
    new S3LambdaNotification(this, "S3LambdaNotification", {
      bucket: storage.kbDocsBucket,
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

    // enable direct lambda testing — regression tests bypass slack infrastructure
    if (runRegressionTests) {
      const regressionTestRole = Role.fromRoleArn(
        this,
        "regressionTestRole",
        regressionTestRoleArn, {
          mutable: true
        })

      const regressionTestPolicy = new ManagedPolicy(this, "RegressionTestPolicy", {
        description: "regression test cross-account invoke permission for direct ai validation",
        statements: [
          new PolicyStatement({
            actions: [
              "lambda:InvokeFunction"
            ],
            resources: [
              functions.slackBotLambda.function.functionArn
            ]
          }),
          new PolicyStatement({
            actions: [
              "cloudformation:ListStacks",
              "cloudformation:DescribeStacks"
            ],
            resources: ["*"]
          })
        ]
      })
      regressionTestRole.addManagedPolicy(regressionTestPolicy)
    }

    // Output: SlackBot Endpoint
    new CfnOutput(this, "SlackBotEventsEndpoint", {
      value: `https://${apis.apis["api"].api.domainName?.domainName}/slack/events`,
      description: "Slack Events API endpoint for @mentions and direct messages"
    })

    // Output: SlackBot Endpoint
    new CfnOutput(this, "SlackBotCommandsEndpoint", {
      value: `https://${apis.apis["api"].api.domainName?.domainName}/slack/commands`,
      description: "Slack Commands API endpoint for slash commands"
    })

    // Output: Bedrock Prompt ARN
    new CfnOutput(this, "QueryReformulationPromptArn", {
      value: bedrockPromptResources.queryReformulationPrompt.promptArn,
      description: "ARN of the query reformulation prompt in Bedrock"
    })

    new CfnOutput(this, "kbDocsBucketArn", {
      value: storage.kbDocsBucket.bucketArn,
      exportName: `${props.stackName}:kbDocsBucket:Arn`
    })
    new CfnOutput(this, "kbDocsBucketName", {
      value: storage.kbDocsBucket.bucketName,
      exportName: `${props.stackName}:kbDocsBucket:Name`
    })

    new CfnOutput(this, "SlackBotLambdaRoleArn", {
      value: functions.slackBotLambda.executionRole.roleArn,
      exportName: `${props.stackName}:lambda:SlackBot:ExecutionRole:Arn`
    })

    new CfnOutput(this, "SlackBotLambdaArn", {
      value: functions.slackBotLambda.function.functionArn,
      exportName: `${props.stackName}:lambda:SlackBot:Arn`
    })

    new CfnOutput(this, "SlackBotLambdaName", {
      value: functions.slackBotLambda.function.functionName,
      exportName: `${props.stackName}:lambda:SlackBot:FunctionName`
    })

    new CfnOutput(this, "ModelInvocationLogGroupName", {
      value: bedrockLogging.modelInvocationLogGroup.logGroupName,
      description: "CloudWatch Log Group for Bedrock model invocations"
    })

    new CfnOutput(this, "KnowledgeBaseLogGroupName", {
      value: vectorKB.kbLogGroup.logGroupName,
      description: "CloudWatch Log Group for Knowledge Base application logs"
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
    nagSuppressions(this, account)
  }
}
