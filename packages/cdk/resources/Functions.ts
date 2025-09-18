import {Construct} from "constructs"
import {LambdaFunction} from "../constructs/LambdaFunction"
import {ManagedPolicy, PolicyStatement, Role} from "aws-cdk-lib/aws-iam"
import {StringParameter} from "aws-cdk-lib/aws-ssm"
import {Secret} from "aws-cdk-lib/aws-secretsmanager"
import {TableV2} from "aws-cdk-lib/aws-dynamodb"

// Claude model for RAG responses
const RAG_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
// Claude model for query reformulation
const QUERY_REFORMULATION_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
const QUERY_REFORMULATION_PROMPT_VERSION = "DRAFT"
const BEDROCK_KB_DATA_SOURCE = "eps-assist-kb-ds"
const LAMBDA_MEMORY_SIZE = "265"

export interface FunctionsProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
  readonly logRetentionInDays: number
  readonly logLevel: string
  readonly createIndexManagedPolicy: ManagedPolicy
  readonly slackBotManagedPolicy: ManagedPolicy
  readonly slackBotTokenParameter: StringParameter
  readonly syncKnowledgeBaseManagedPolicy: ManagedPolicy
  readonly slackSigningSecretParameter: StringParameter
  readonly guardrailId: string
  readonly guardrailVersion: string
  readonly collectionId: string
  readonly knowledgeBaseId: string
  readonly dataSourceId: string
  readonly region: string
  readonly account: string
  readonly slackBotTokenSecret: Secret
  readonly slackBotSigningSecret: Secret
  readonly slackBotStateTable: TableV2
  readonly promptName: string
  readonly isPullRequest: boolean
  readonly mainSlackBotLambdaExecutionRoleArn : string
}

export class Functions extends Construct {
  public readonly slackBotLambda: LambdaFunction
  public readonly syncKnowledgeBaseFunction: LambdaFunction

  constructor(scope: Construct, id: string, props: FunctionsProps) {
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
        "RAG_MODEL_ID": RAG_MODEL_ID,
        "QUERY_REFORMULATION_MODEL_ID": QUERY_REFORMULATION_MODEL_ID,
        "KNOWLEDGEBASE_ID": props.knowledgeBaseId,
        "BEDROCK_KB_DATA_SOURCE": BEDROCK_KB_DATA_SOURCE,
        "LAMBDA_MEMORY_SIZE": LAMBDA_MEMORY_SIZE,
        "SLACK_BOT_TOKEN_PARAMETER": props.slackBotTokenParameter.parameterName,
        "SLACK_SIGNING_SECRET_PARAMETER": props.slackSigningSecretParameter.parameterName,
        "GUARD_RAIL_ID": props.guardrailId,
        "GUARD_RAIL_VERSION": props.guardrailVersion,
        "SLACK_BOT_STATE_TABLE": props.slackBotStateTable.tableName,
        "QUERY_REFORMULATION_PROMPT_NAME": props.promptName,
        "QUERY_REFORMULATION_PROMPT_VERSION": QUERY_REFORMULATION_PROMPT_VERSION
      }
    })

    // Grant secrets access to SlackBot Lambda
    props.slackBotTokenSecret.grantRead(slackBotLambda.function)
    props.slackBotSigningSecret.grantRead(slackBotLambda.function)

    if (props.isPullRequest) {
      const mainSlackBotLambdaExecutionRole = Role.fromRoleArn(
        this,
        "mainRoleArn",
        props.mainSlackBotLambdaExecutionRoleArn, {
          mutable: true
        })

      const executeSlackBotPolicy = new ManagedPolicy(this, "ExecuteSlackBotPolicy", {
        description: "foo",
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

    // Lambda function to sync knowledge base on S3 events
    const syncKnowledgeBaseFunction = new LambdaFunction(this, "SyncKnowledgeBaseFunction", {
      stackName: props.stackName,
      functionName: `${props.stackName}-SyncKnowledgeBaseFunction`,
      packageBasePath: "packages/syncKnowledgeBaseFunction",
      handler: "app.handler.handler",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      dependencyLocation: ".dependencies/syncKnowledgeBaseFunction",
      environmentVariables: {
        "KNOWLEDGEBASE_ID": props.knowledgeBaseId,
        "DATA_SOURCE_ID": props.dataSourceId
      },
      additionalPolicies: [props.syncKnowledgeBaseManagedPolicy]
    })

    this.slackBotLambda = slackBotLambda
    this.syncKnowledgeBaseFunction = syncKnowledgeBaseFunction
  }
}
