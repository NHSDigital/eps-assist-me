import {Construct} from "constructs"
import {LambdaFunction} from "../constructs/LambdaFunction"
import {ManagedPolicy, PolicyStatement, Role} from "aws-cdk-lib/aws-iam"
import {StringParameter} from "aws-cdk-lib/aws-ssm"

const LAMBDA_MEMORY_SIZE = "265"

export interface StatelessFunctionsProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
  readonly logRetentionInDays: number
  readonly logLevel: string
  readonly slackBotManagedPolicy: ManagedPolicy
  readonly slackBotTokenParameter: StringParameter
  readonly slackSigningSecretParameter: StringParameter
  readonly guardrailId: string
  readonly guardrailVersion: string
  readonly knowledgeBaseId: string
  readonly slackBotStateTableName: string
  readonly reformulationPromptName: string
  readonly ragResponsePromptName: string
  readonly reformulationPromptVersion: string
  readonly ragResponsePromptVersion: string
  readonly isPullRequest: boolean
  readonly mainSlackBotLambdaExecutionRoleArn : string
  readonly ragModelId: string
  readonly queryReformulationModelId: string
}

export class StatelessFunctions extends Construct {
  public readonly slackBotLambda: LambdaFunction

  constructor(scope: Construct, id: string, props: StatelessFunctionsProps) {
    super(scope, id)

    // Lambda function to handle Slack bot interactions (events and @mentions)
    const slackBotLambda = new LambdaFunction(this, "SlackBotLambda", {
      stackName: props.stackName,
      functionName: `${props.stackName}-SlackBotFunction`,
      packageBasePath: "packages/slackBotFunction",
      handler: "app.handler.handler",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      additionalPolicies: [props.slackBotManagedPolicy],
      dependencyLocation: ".dependencies/slackBotFunction",
      environmentVariables: {
        "RAG_MODEL_ID": props.ragModelId,
        "QUERY_REFORMULATION_MODEL_ID": props.queryReformulationModelId,
        "KNOWLEDGEBASE_ID": props.knowledgeBaseId,
        "LAMBDA_MEMORY_SIZE": LAMBDA_MEMORY_SIZE,
        "SLACK_BOT_TOKEN_PARAMETER": props.slackBotTokenParameter.parameterName,
        "SLACK_SIGNING_SECRET_PARAMETER": props.slackSigningSecretParameter.parameterName,
        "GUARD_RAIL_ID": props.guardrailId,
        "GUARD_RAIL_VERSION": props.guardrailVersion,
        "SLACK_BOT_STATE_TABLE": props.slackBotStateTableName,
        "QUERY_REFORMULATION_PROMPT_NAME": props.reformulationPromptName,
        "RAG_RESPONSE_PROMPT_NAME": props.ragResponsePromptName,
        "QUERY_REFORMULATION_PROMPT_VERSION": props.reformulationPromptVersion,
        "RAG_RESPONSE_PROMPT_VERSION": props.ragResponsePromptVersion,
        "STACK_NAME": props.stackName
      }
    })

    // pr environments need main bot to invoke pr-specific lambda
    if (props.isPullRequest) {
      const mainSlackBotLambdaExecutionRole = Role.fromRoleArn(
        this,
        "mainRoleArn",
        props.mainSlackBotLambdaExecutionRoleArn, {
          mutable: true
        })

      const executeSlackBotPolicy = new ManagedPolicy(this, "ExecuteSlackBotPolicy", {
        description: "cross-lambda invocation for pr: command routing",
        statements: [
          new PolicyStatement({
            actions: [
              "lambda:invokeFunction"
            ],
            resources: [
              slackBotLambda.function.functionArn
            ]
          })
        ]
      })
      mainSlackBotLambdaExecutionRole.addManagedPolicy(executeSlackBotPolicy)
    }

    this.slackBotLambda = slackBotLambda
  }
}
