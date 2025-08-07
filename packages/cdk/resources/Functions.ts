import {Construct} from "constructs"
import {LambdaFunction} from "../constructs/LambdaFunction"
import {ManagedPolicy} from "aws-cdk-lib/aws-iam"
import {StringParameter} from "aws-cdk-lib/aws-ssm"
import {Secret} from "aws-cdk-lib/aws-secretsmanager"

// Claude model for RAG responses
const RAG_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
const SLACK_SLASH_COMMAND = "/ask-eps"
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
  readonly slackSigningSecretParameter: StringParameter
  readonly guardrailId: string
  readonly guardrailVersion: string
  readonly collectionId: string
  readonly knowledgeBaseId: string
  readonly region: string
  readonly account: string
  readonly slackBotTokenSecret: Secret
  readonly slackBotSigningSecret: Secret
  readonly conversationTableName: string
}

export class Functions extends Construct {
  public readonly functions: {[key: string]: LambdaFunction}

  constructor(scope: Construct, id: string, props: FunctionsProps) {
    super(scope, id)

    // Lambda function to create OpenSearch vector index
    const createIndexFunction = new LambdaFunction(this, "CreateIndexFunction", {
      stackName: props.stackName,
      functionName: `${props.stackName}-CreateIndexFunction`,
      packageBasePath: "packages/createIndexFunction",
      entryPoint: "app.py",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      environmentVariables: {"INDEX_NAME": props.collectionId},
      additionalPolicies: [props.createIndexManagedPolicy]
    })

    // Lambda function to handle Slack bot interactions
    const slackBotLambda = new LambdaFunction(this, "SlackBotLambda", {
      stackName: props.stackName,
      functionName: `${props.stackName}-SlackBotFunction`,
      packageBasePath: "packages/slackBotFunction",
      entryPoint: "app.py",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      additionalPolicies: [props.slackBotManagedPolicy],
      environmentVariables: {
        "RAG_MODEL_ID": RAG_MODEL_ID,
        "SLACK_SLASH_COMMAND": SLACK_SLASH_COMMAND,
        "KNOWLEDGEBASE_ID": props.knowledgeBaseId || "placeholder",
        "BEDROCK_KB_DATA_SOURCE": BEDROCK_KB_DATA_SOURCE,
        "LAMBDA_MEMORY_SIZE": LAMBDA_MEMORY_SIZE,
        "SLACK_BOT_TOKEN_PARAMETER": props.slackBotTokenParameter.parameterName,
        "SLACK_SIGNING_SECRET_PARAMETER": props.slackSigningSecretParameter.parameterName,
        "GUARD_RAIL_ID": props.guardrailId || "placeholder",
        "GUARD_RAIL_VERSION": props.guardrailVersion || "placeholder",
        "CONVERSATION_TABLE_NAME": props.conversationTableName
      }
    })

    // Grant secrets access to SlackBot Lambda
    props.slackBotTokenSecret.grantRead(slackBotLambda.function)
    props.slackBotSigningSecret.grantRead(slackBotLambda.function)

    this.functions = {
      createIndex: createIndexFunction,
      slackBot: slackBotLambda
    }
  }
}
