import {
  App,
  Stack,
  StackProps,
  CfnOutput,
  Fn
} from "aws-cdk-lib"
import {statelessNagSuppressions} from "../nagSuppressions"
import {Apis} from "../resources/Apis"
import {Secrets} from "../resources/Secrets"
import {BedrockPromptResources} from "../resources/BedrockPromptResources"
import {ManagedPolicy, PolicyStatement, Role} from "aws-cdk-lib/aws-iam"
import {BedrockPromptSettings} from "../resources/BedrockPromptSettings"
import {StatelessRuntimePolicies} from "../resources/StatelessRuntimePolicies"
import {GuardRailResources} from "../resources/GuardRailResources"
import {StatelessFunctions} from "../resources/StatelessFunctions"
import {StringParameter} from "aws-cdk-lib/aws-ssm"

export interface EpsAssistMeStatelessProps extends StackProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
  readonly region: string
  readonly logRetentionInDays: number
  readonly logLevel: string
  readonly isPullRequest: boolean
  readonly runRegressionTests: boolean
  readonly forwardCsocLogs: boolean
  readonly csocApiGatewayDestination: string
  readonly slackBotToken: string
  readonly slackSigningSecret: string
  readonly statefulStackName: string
}

export class EpsAssistMe_Stateless extends Stack {
  public constructor(scope: App, id: string, props: EpsAssistMeStatelessProps) {
    super(scope, id, props)

    // imports
    const mainSlackBotLambdaExecutionRoleArn = Fn.importValue("epsam:lambda:SlackBot:ExecutionRole:Arn")
    // regression testing needs direct lambda invoke — bypasses slack webhooks entirely
    const regressionTestRoleArn = Fn.importValue("ci-resources:AssistMeRegressionTestRole")

    const slackBotStateTableArn = Fn.importValue(`${props.statefulStackName}:slackBotStateTable:Arn`)
    const slackBotStateTableName = Fn.importValue(`${props.statefulStackName}:slackBotStateTable:Name`)
    const slackBotStateTableKmsKeyArn = Fn.importValue(`${props.statefulStackName}:slackBotStateTable:kmsKey:Arn`)
    const knowledgeBaseArn = Fn.importValue(`${props.statefulStackName}:knowledgeBase:Arn`)
    const knowledgeBaseId = Fn.importValue(`${props.statefulStackName}:knowledgeBase:Id`)

    if (!props.slackBotToken || !props.slackSigningSecret) {
      throw new Error("Missing required context variables. Please provide slackBotToken and slackSigningSecret")
    }
    const account = Stack.of(this).account

    // Create Secrets construct
    const secrets = new Secrets(this, "Secrets", {
      stackName: props.stackName,
      slackBotToken: props.slackBotToken,
      slackSigningSecret: props.slackSigningSecret
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
      region: props.region,
      account: account,
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
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
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
      isPullRequest: props.isPullRequest,
      mainSlackBotLambdaExecutionRoleArn: mainSlackBotLambdaExecutionRoleArn
    })

    // Create Apis and pass the Lambda function
    const apis = new Apis(this, "Apis", {
      stackName: props.stackName,
      logRetentionInDays: props.logRetentionInDays,
      functions: {
        slackBot: functions.slackBotLambda
      },
      forwardCsocLogs: props.forwardCsocLogs,
      csocApiGatewayDestination: props.csocApiGatewayDestination
    })

    // enable direct lambda testing — regression tests bypass slack infrastructure
    if (props.runRegressionTests) {
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

    new StringParameter(this, "ApiUrlParam", {
      parameterName: `/${props.stackName}/apiGateway/restApiId`,
      stringValue: apis.apiGateway.api.restApiId
    })
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

    if (props.isPullRequest) {
      new CfnOutput(this, "VERSION_NUMBER", {
        value: props.version,
        exportName: `${props.stackName}:local:VERSION-NUMBER`
      })
      new CfnOutput(this, "COMMIT_ID", {
        value: props.commitId,
        exportName: `${props.stackName}:local:COMMIT-ID`
      })
      new CfnOutput(this, "slackBotToken", {
        value: props.slackBotToken,
        exportName: `${props.stackName}:local:slackBotToken`
      })
      new CfnOutput(this, "slackSigningSecret", {
        value: props.slackSigningSecret,
        exportName: `${props.stackName}:local:slackSigningSecret`
      })
    }
    new CfnOutput(this, "ApigatewayId", {
      value: apis.apiGateway.api.restApiId,
      exportName: `${props.stackName}:apiGateway:api:RestApiId`
    })

    // Final CDK Nag Suppressions
    statelessNagSuppressions(this, account)
  }
}
