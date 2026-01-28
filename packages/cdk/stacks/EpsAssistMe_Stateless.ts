import {
  App,
  Stack,
  StackProps,
  CfnOutput,
  Fn
} from "aws-cdk-lib"
import {nagSuppressions} from "../nagSuppressions"
import {Apis} from "../resources/Apis"
import {Secrets} from "../resources/Secrets"
import {BedrockPromptResources} from "../resources/BedrockPromptResources"
import {ManagedPolicy, PolicyStatement, Role} from "aws-cdk-lib/aws-iam"
import {BedrockPromptSettings} from "../resources/BedrockPromptSettings"
import {StatelessRuntimePolicies} from "../resources/StatelessRuntimePolicies"
import {GuardRailResources} from "../resources/GuardRailResources"
import {StatelessFunctions} from "../resources/StatelessFunctions"

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
    const regressionTestRoleArn = Fn.importValue("ci-resources:AssistMeRegressionTestRole")

    const slackBotStateTableArn = Fn.importValue("<CHANGE ME>")
    const slackBotStateTableName = Fn.importValue("<CHANGE ME>")
    const slackBotStateTableKmsKeyArn = Fn.importValue("<CHANGE ME>")
    const knowledgeBaseArn = Fn.importValue("<CHANGE ME>")
    const knowledgeBaseId = Fn.importValue("<CHANGE ME>")

    // Get variables from context
    const region = Stack.of(this).region
    const account = Stack.of(this).account

    const logRetentionInDays = Number(this.node.tryGetContext("logRetentionInDays"))
    const logLevel: string = this.node.tryGetContext("logLevel")
    const isPullRequest: boolean = this.node.tryGetContext("isPullRequest")
    const runRegressionTests: boolean = this.node.tryGetContext("runRegressionTests")
    const forwardCsocLogs: boolean = this.node.tryGetContext("forwardCsocLogs")
    const csocApiGatewayDestination: string = this.node.tryGetContext("csocApiGatewayDestination")

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

    // Create Bedrock Prompt Collection
    const bedrockPromptCollection = new BedrockPromptSettings(this, "BedrockPromptCollection")

    // Create Bedrock Prompt Resources
    const bedrockPromptResources = new BedrockPromptResources(this, "BedrockPromptResources", {
      stackName: props.stackName,
      settings: bedrockPromptCollection
    })

    const guardRailResources = new GuardRailResources(this, "GuardRailResources", {
      stackName: props.stackName
    })
    // Create runtime policies with resource dependencies
    const runtimePolicies = new StatelessRuntimePolicies(this, "RuntimePolicies", {
      region,
      account,
      slackBotTokenParameterName: secrets.slackBotTokenParameter.parameterName,
      slackSigningSecretParameterName: secrets.slackSigningSecretParameter.parameterName,
      slackBotStateTableArn: slackBotStateTableArn,
      slackBotStateTableKmsKeyArn: slackBotStateTableKmsKeyArn,
      knowledgeBaseArn: knowledgeBaseArn,
      guardrailArn: guardRailResources.guardrail.guardrailArn,
      ragModelId: bedrockPromptResources.ragModelId,
      queryReformulationModelId: bedrockPromptResources.queryReformulationModelId
    })

    // Create Functions construct with actual values from VectorKB
    const functions = new StatelessFunctions(this, "Functions", {
      stackName: props.stackName,
      version: props.version,
      commitId: props.commitId,
      logRetentionInDays,
      logLevel,
      slackBotManagedPolicy: runtimePolicies.slackBotPolicy,
      slackBotTokenParameter: secrets.slackBotTokenParameter,
      slackSigningSecretParameter: secrets.slackSigningSecretParameter,
      guardrailId: guardRailResources.guardrail.guardrailId,
      guardrailVersion: guardRailResources.guardrail.guardrailVersion,
      knowledgeBaseId: knowledgeBaseId,
      slackBotStateTableName: slackBotStateTableName,
      reformulationPromptName: bedrockPromptResources.queryReformulationPrompt.promptName,
      ragResponsePromptName: bedrockPromptResources.ragResponsePrompt.promptName,
      reformulationPromptVersion: bedrockPromptResources.queryReformulationPrompt.promptVersion,
      ragResponsePromptVersion: bedrockPromptResources.ragResponsePrompt.promptVersion,
      ragModelId: bedrockPromptResources.ragModelId,
      queryReformulationModelId: bedrockPromptResources.queryReformulationModelId,
      isPullRequest: isPullRequest,
      mainSlackBotLambdaExecutionRoleArn: mainSlackBotLambdaExecutionRoleArn
    })

    // Create Apis and pass the Lambda function
    const apis = new Apis(this, "Apis", {
      stackName: props.stackName,
      logRetentionInDays,
      functions: {
        slackBot: functions.slackBotLambda
      },
      forwardCsocLogs,
      csocApiGatewayDestination
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
            resources: [`arn:aws:cloudformation:eu-west-2:${account}:stack/epsam*`]
          })
        ]
      })
      regressionTestRole.addManagedPolicy(regressionTestPolicy)
    }

    // Output: SlackBot Endpoint
    new CfnOutput(this, "SlackBotEventsEndpoint", {
      value: `https://${apis.apiGateway.api.domainName?.domainName}/slack/events`,
      description: "Slack Events API endpoint for @mentions and direct messages"
    })

    // Output: SlackBot Endpoint
    new CfnOutput(this, "SlackBotCommandsEndpoint", {
      value: `https://${apis.apiGateway.api.domainName?.domainName}/slack/commands`,
      description: "Slack Commands API endpoint for slash commands"
    })

    // Output: Bedrock Prompt ARN
    new CfnOutput(this, "QueryReformulationPromptArn", {
      value: bedrockPromptResources.queryReformulationPrompt.promptArn,
      description: "ARN of the query reformulation prompt in Bedrock"
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
    new CfnOutput(this, "ApigatewayId", {
      value: apis.apiGateway.api.restApiId,
      exportName: `${props.stackName}:apiGateway:api:RestApiId`
    })

    // Final CDK Nag Suppressions
    nagSuppressions(this, account)
  }
}
