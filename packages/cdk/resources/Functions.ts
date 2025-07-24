import {Construct} from "constructs"
import {LambdaFunction} from "../constructs/LambdaFunction"
import {Role, PolicyStatement} from "aws-cdk-lib/aws-iam"
import * as ssm from "aws-cdk-lib/aws-ssm"
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager"

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
  createIndexFunctionRole: Role
  slackBotTokenParameter: ssm.StringParameter
  slackSigningSecretParameter: ssm.StringParameter
  guardrailId: string
  guardrailVersion: string
  collectionId: string
  knowledgeBaseId: string
  region: string
  account: string
  slackBotTokenSecret: secretsmanager.Secret
  slackBotSigningSecret: secretsmanager.Secret
}

export class Functions extends Construct {
  public readonly functions: {[key: string]: LambdaFunction}

  constructor(scope: Construct, id: string, props: FunctionsProps) {
    super(scope, id)

    const createIndexFunction = new LambdaFunction(this, "CreateIndexFunction", {
      stackName: props.stackName,
      functionName: `${props.stackName}-CreateIndexFunction`,
      packageBasePath: "packages/createIndexFunction",
      entryPoint: "app.py",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      environmentVariables: {"INDEX_NAME": props.collectionId},
      additionalPolicies: [],
      role: props.createIndexFunctionRole
    })

    const slackBotLambda = new LambdaFunction(this, "SlackBotLambda", {
      stackName: props.stackName,
      functionName: `${props.stackName}-SlackBotFunction`,
      packageBasePath: "packages/slackBotFunction",
      entryPoint: "app.py",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      additionalPolicies: [],
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

    // Create Lambda policies
    const lambdaBedrockModelPolicy = new PolicyStatement()
    lambdaBedrockModelPolicy.addActions("bedrock:InvokeModel")
    lambdaBedrockModelPolicy.addResources(`arn:aws:bedrock:${props.region}::foundation-model/${RAG_MODEL_ID}`)

    const lambdaBedrockKbPolicy = new PolicyStatement()
    lambdaBedrockKbPolicy.addActions("bedrock:Retrieve")
    lambdaBedrockKbPolicy.addActions("bedrock:RetrieveAndGenerate")
    lambdaBedrockKbPolicy.addResources(
      `arn:aws:bedrock:${props.region}:${props.account}:knowledge-base/${props.knowledgeBaseId}`
    )

    const lambdaSSMPolicy = new PolicyStatement()
    lambdaSSMPolicy.addActions("ssm:GetParameter")
    lambdaSSMPolicy.addResources(
      `arn:aws:ssm:${props.region}:${props.account}:parameter${props.slackBotTokenParameter.parameterName}`)
    lambdaSSMPolicy.addResources(
      `arn:aws:ssm:${props.region}:${props.account}:parameter${props.slackSigningSecretParameter.parameterName}`)

    const lambdaReinvokePolicy = new PolicyStatement()
    lambdaReinvokePolicy.addActions("lambda:InvokeFunction")
    lambdaReinvokePolicy.addResources(`arn:aws:lambda:${props.region}:${props.account}:function:*`)

    const lambdaGRinvokePolicy = new PolicyStatement()
    lambdaGRinvokePolicy.addActions("bedrock:ApplyGuardrail")
    lambdaGRinvokePolicy.addResources(`arn:aws:bedrock:${props.region}:${props.account}:guardrail/*`)

    // Grant secrets access and attach policies
    props.slackBotTokenSecret.grantRead(slackBotLambda.function)
    props.slackBotSigningSecret.grantRead(slackBotLambda.function)

    slackBotLambda.function.addToRolePolicy(lambdaBedrockModelPolicy)
    slackBotLambda.function.addToRolePolicy(lambdaBedrockKbPolicy)
    slackBotLambda.function.addToRolePolicy(lambdaReinvokePolicy)
    slackBotLambda.function.addToRolePolicy(lambdaGRinvokePolicy)
    slackBotLambda.function.addToRolePolicy(lambdaSSMPolicy)

    this.functions = {
      createIndex: createIndexFunction,
      slackBot: slackBotLambda
    }
  }
}
