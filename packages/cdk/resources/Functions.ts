import {Construct} from "constructs"
import {PythonLambdaFunction} from "@nhsdigital/eps-cdk-constructs"
import {ManagedPolicy, PolicyStatement, Role} from "aws-cdk-lib/aws-iam"
import {StringParameter} from "aws-cdk-lib/aws-ssm"
import {Secret} from "aws-cdk-lib/aws-secretsmanager"
import {TableV2} from "aws-cdk-lib/aws-dynamodb"
import {resolve} from "path"

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
  readonly reformulationModelId: string
  readonly docsBucketName: string
  readonly knowledgeSyncStateTable: TableV2
}

export class Functions extends Construct {
  public readonly slackBotLambda: PythonLambdaFunction
  public readonly syncKnowledgeBaseFunction: PythonLambdaFunction
  public readonly preprocessingFunction: PythonLambdaFunction

  constructor(scope: Construct, id: string, props: FunctionsProps) {
    super(scope, id)

    // Lambda function to handle Slack bot interactions (events and @mentions)
    const slackBotLambda = new PythonLambdaFunction(this, "SlackBotLambda", {
      functionName: `${props.stackName}-SlackBotFunction`,
      projectBaseDir: resolve(__dirname, "../../.."),
      packageBasePath: "packages/slackBotFunction",
      handler: "app.handler.handler",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      additionalPolicies: [props.slackBotManagedPolicy],
      dependencyLocation: ".dependencies/slackBotFunction",
      environmentVariables: {
        "RAG_MODEL_ID": props.ragModelId,
        "REFORMULATION_MODEL_ID": props.reformulationModelId,
        "KNOWLEDGEBASE_ID": props.knowledgeBaseId,
        "LAMBDA_MEMORY_SIZE": LAMBDA_MEMORY_SIZE,
        "SLACK_BOT_TOKEN_PARAMETER": props.slackBotTokenParameter.parameterName,
        "SLACK_SIGNING_SECRET_PARAMETER": props.slackSigningSecretParameter.parameterName,
        "GUARD_RAIL_ID": props.guardrailId,
        "GUARD_RAIL_VERSION": props.guardrailVersion,
        "SLACK_BOT_STATE_TABLE": props.slackBotStateTable.tableName,
        "REFORMULATION_RESPONSE_PROMPT_NAME": props.reformulationPromptName,
        "RAG_RESPONSE_PROMPT_NAME": props.ragResponsePromptName,
        "REFORMULATION_RESPONSE_PROMPT_VERSION": props.reformulationPromptVersion,
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
    const preprocessingFunction = new PythonLambdaFunction(this, "PreprocessingFunction", {
      functionName: `${props.stackName}-PreprocessingFunction`,
      projectBaseDir: resolve(__dirname, "../../.."),
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
    const syncKnowledgeBaseFunction = new PythonLambdaFunction(this, "SyncKnowledgeBaseFunction", {
      functionName: `${props.stackName}-SyncKnowledgeBaseFunction`,
      projectBaseDir: resolve(__dirname, "../../.."),
      packageBasePath: "packages/syncKnowledgeBaseFunction",
      handler: "app.handler.handler",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      dependencyLocation: ".dependencies/syncKnowledgeBaseFunction",
      environmentVariables: {
        "KNOWLEDGEBASE_ID": props.knowledgeBaseId,
        "SLACK_BOT_TOKEN_PARAMETER": props.slackBotTokenParameter.parameterName,
        "SLACK_BOT_ACTIVE": `${!props.isPullRequest}`,
        "DATA_SOURCE_ID": props.dataSourceId,
        "KNOWLEDGE_SYNC_STATE_TABLE": props.knowledgeSyncStateTable.tableName
      },
      additionalPolicies: [props.syncKnowledgeBaseManagedPolicy]
    })

    this.slackBotLambda = slackBotLambda
    this.preprocessingFunction = preprocessingFunction
    this.syncKnowledgeBaseFunction = syncKnowledgeBaseFunction
  }
}
