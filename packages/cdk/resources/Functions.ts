import {Construct} from "constructs"
import {LambdaFunction} from "../constructs/LambdaFunction"
import {PolicyStatement, ManagedPolicy} from "aws-cdk-lib/aws-iam"
import {StringParameter} from "aws-cdk-lib/aws-ssm"
import {Secret} from "aws-cdk-lib/aws-secretsmanager"

// Claude model for RAG responses
const RAG_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
const SLACK_SLASH_COMMAND = "/ask-eps"
const BEDROCK_KB_DATA_SOURCE = "eps-assist-kb-ds"
const LAMBDA_MEMORY_SIZE = "265"

export interface FunctionsProps {
  stackName: string
  version: string
  commitId: string
  logRetentionInDays: number
  logLevel: string
  createIndexManagedPolicy: ManagedPolicy
  slackBotTokenParameter: StringParameter
  slackSigningSecretParameter: StringParameter
  guardrailId: string
  guardrailVersion: string
  collectionId: string
  knowledgeBaseId: string
  region: string
  account: string
  slackBotTokenSecret: Secret
  slackBotSigningSecret: Secret
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

    // Create managed policies for SlackBot Lambda
    const slackBotManagedPolicy = new ManagedPolicy(this, "SlackBotManagedPolicy", {
      description: "Policy for SlackBot Lambda to access Bedrock, SSM, and Lambda",
      statements: [
        new PolicyStatement({
          actions: ["bedrock:InvokeModel"],
          resources: [`arn:aws:bedrock:${props.region}::foundation-model/${RAG_MODEL_ID}`]
        }),
        new PolicyStatement({
          actions: ["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
          resources: [`arn:aws:bedrock:${props.region}:${props.account}:knowledge-base/${props.knowledgeBaseId}`]
        }),
        new PolicyStatement({
          actions: ["ssm:GetParameter"],
          resources: [
            `arn:aws:ssm:${props.region}:${props.account}:parameter${props.slackBotTokenParameter.parameterName}`,
            `arn:aws:ssm:${props.region}:${props.account}:parameter${props.slackSigningSecretParameter.parameterName}`
          ]
        }),
        new PolicyStatement({
          actions: ["lambda:InvokeFunction"],
          resources: [`arn:aws:lambda:${props.region}:${props.account}:function:*`]
        }),
        new PolicyStatement({
          actions: ["bedrock:ApplyGuardrail"],
          resources: [`arn:aws:bedrock:${props.region}:${props.account}:guardrail/*`]
        })
      ]
    })

    // Lambda function to handle Slack bot interactions
    const slackBotLambda = new LambdaFunction(this, "SlackBotLambda", {
      stackName: props.stackName,
      functionName: `${props.stackName}-SlackBotFunction`,
      packageBasePath: "packages/slackBotFunction",
      entryPoint: "app.py",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      additionalPolicies: [slackBotManagedPolicy],
      environmentVariables: {
        "RAG_MODEL_ID": RAG_MODEL_ID,
        "SLACK_SLASH_COMMAND": SLACK_SLASH_COMMAND,
        "KNOWLEDGEBASE_ID": props.knowledgeBaseId,
        "BEDROCK_KB_DATA_SOURCE": BEDROCK_KB_DATA_SOURCE,
        "LAMBDA_MEMORY_SIZE": LAMBDA_MEMORY_SIZE,
        "SLACK_BOT_TOKEN_PARAMETER": props.slackBotTokenParameter.parameterName,
        "SLACK_SIGNING_SECRET_PARAMETER": props.slackSigningSecretParameter.parameterName,
        "GUARD_RAIL_ID": props.guardrailId,
        "GUARD_RAIL_VERSION": props.guardrailVersion
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
