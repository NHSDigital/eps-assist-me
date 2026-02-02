import {Construct} from "constructs"
import {LambdaFunction} from "../constructs/LambdaFunction"
import {ManagedPolicy, PolicyStatement, Role} from "aws-cdk-lib/aws-iam"
import {StringParameter} from "aws-cdk-lib/aws-ssm"
import {Secret} from "aws-cdk-lib/aws-secretsmanager"
import {TableV2} from "aws-cdk-lib/aws-dynamodb"

const LAMBDA_MEMORY_SIZE = "265"

export interface FunctionsProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
  readonly logRetentionInDays: number
  readonly logLevel: string
  readonly slackBotManagedPolicy: ManagedPolicy
  readonly slackBotTokenParameter: StringParameter
  readonly syncKnowledgeBaseManagedPolicy: ManagedPolicy
  readonly preprocessingManagedPolicy: ManagedPolicy
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
  readonly reformulationPromptName: string
  readonly ragResponsePromptName: string
  readonly reformulationPromptVersion: string
  readonly ragResponsePromptVersion: string
  readonly isPullRequest: boolean
  readonly mainSlackBotLambdaExecutionRoleArn : string
  readonly ragModelId: string
  readonly queryReformulationModelId: string
  readonly notifyS3UploadFunctionPolicy: ManagedPolicy
  readonly docsBucketName: string
}

export class Functions extends Construct {
  public readonly slackBotLambda: LambdaFunction
  public readonly syncKnowledgeBaseFunction: LambdaFunction
  public readonly notifyS3UploadFunction: LambdaFunction
  public readonly preprocessingFunction: LambdaFunction

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
        "RAG_MODEL_ID": props.ragModelId,
        "QUERY_REFORMULATION_MODEL_ID": props.queryReformulationModelId,
        "KNOWLEDGEBASE_ID": props.knowledgeBaseId,
        "LAMBDA_MEMORY_SIZE": LAMBDA_MEMORY_SIZE,
        "SLACK_BOT_TOKEN_PARAMETER": props.slackBotTokenParameter.parameterName,
        "SLACK_SIGNING_SECRET_PARAMETER": props.slackSigningSecretParameter.parameterName,
        "GUARD_RAIL_ID": props.guardrailId,
        "GUARD_RAIL_VERSION": props.guardrailVersion,
        "SLACK_BOT_STATE_TABLE": props.slackBotStateTable.tableName,
        "QUERY_REFORMULATION_PROMPT_NAME": props.reformulationPromptName,
        "RAG_RESPONSE_PROMPT_NAME": props.ragResponsePromptName,
        "QUERY_REFORMULATION_PROMPT_VERSION": props.reformulationPromptVersion,
        "RAG_RESPONSE_PROMPT_VERSION": props.ragResponsePromptVersion
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

    // Lambda function to preprocess documents (convert to markdown)
    const preprocessingFunction = new LambdaFunction(this, "PreprocessingFunction", {
      stackName: props.stackName,
      functionName: `${props.stackName}-PreprocessingFunction`,
      packageBasePath: "packages/preprocessingFunction",
      handler: "app.handler.handler",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      dependencyLocation: ".dependencies/preprocessingFunction",
      environmentVariables: {
        "DOCS_BUCKET_NAME": props.docsBucketName,
        "RAW_PREFIX": "raw/",
        "PROCESSED_PREFIX": "processed/",
        "AWS_ACCOUNT_ID": props.account
      },
      additionalPolicies: [props.preprocessingManagedPolicy]
    })

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

    const notifyS3UploadFunction = new LambdaFunction(this, "NotifyS3UploadFunction", {
      stackName: props.stackName,
      functionName: `${props.stackName}-S3UpdateFunction`,
      packageBasePath: "packages/notifyS3UploadFunction",
      handler: "app.handler.handler",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      dependencyLocation: ".dependencies/notifyS3UploadFunction",
      environmentVariables: {
        "SLACK_BOT_TOKEN_PARAMETER": props.slackBotTokenParameter.parameterName
      },
      additionalPolicies: [props.notifyS3UploadFunctionPolicy]
    })

    this.slackBotLambda = slackBotLambda
    this.preprocessingFunction = preprocessingFunction
    this.syncKnowledgeBaseFunction = syncKnowledgeBaseFunction
    this.notifyS3UploadFunction = notifyS3UploadFunction
  }
}
