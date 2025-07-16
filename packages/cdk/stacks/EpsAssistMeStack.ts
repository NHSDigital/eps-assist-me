import {
  Stack,
  StackProps,
  Duration,
  RemovalPolicy,
  Fn,
  CfnOutput
} from "aws-cdk-lib"
import {Construct} from "constructs"
import {Bucket, BucketEncryption} from "aws-cdk-lib/aws-s3"
import {Key} from "aws-cdk-lib/aws-kms"
import {
  PolicyStatement,
  Role,
  ServicePrincipal,
  ManagedPolicy
} from "aws-cdk-lib/aws-iam"
import {RestApiGateway} from "../resources/RestApiGateway"
import {LambdaFunction} from "../resources/LambdaFunction"
import {LambdaIntegration} from "aws-cdk-lib/aws-apigateway"
import {PythonFunction} from "@aws-cdk/aws-lambda-python-alpha"
import * as path from "path"
import * as bedrock from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock"
import {nagSuppressions} from "../nagSuppressions"


const RAG_MODEL_ID = process.env.RAG_MODEL_ID
const EMBEDDING_MODEL = process.env.EMBEDDING_MODEL
const SLACK_SLASH_COMMAND = process.env.SLACK_SLASH_COMMAND
const COLLECTION_NAME = process.env.COLLECTION_NAME
const VECTOR_INDEX_NAME = process.env.VECTOR_INDEX_NAME
const BEDROCK_KB_NAME = process.env.BEDROCK_KB_NAME
const BEDROCK_KB_DATA_SOURCE = process.env.BEDROCK_KB_DATA_SOURCE
const LAMBDA_MEMORY_SIZE = process.env.LAMBDA_MEMORY_SIZE

const GUARD_RAIL_ID = process.env.GUARD_RAIL_ID
const GUARD_RAIL_VERSION = process.env.GUARD_RAIL_VERSION
const SLACK_BOT_TOKEN_PARAMETER = process.env.SLACK_BOT_TOKEN_PARAMETER
const SLACK_SIGNING_SECRET_PARAMETER = process.env.SLACK_SIGNING_SECRET_PARAMETER




export interface EpsAssistMeStackProps extends StackProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
  readonly logRetentionInDays: number
  readonly logLevel: string
}

export class EpsAssistMeStack extends Stack {
  constructor(scope: Construct, id: string, props: EpsAssistMeStackProps) {
    super(scope, id, props)

    // KMS Key
    const kmsKey = new Key(this, "EpsKmsKey", {
      enableKeyRotation: true
    })

    // S3 Bucket with custom KMS
    const kbDocsBucket = new Bucket(this, "EpsAssistDocsBucket", {
      encryption: BucketEncryption.KMS,
      encryptionKey: kmsKey,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true
    })

    // API Gateway with Custom Domain
    const apiGateway = new RestApiGateway(this, "EpsAssistApiGateway", {
      stackName: "eps-assist-me",
      logRetentionInDays: 14,
      enableMutualTls: false,
      trustStoreKey: "unused",
      truststoreVersion: "unused"
    })

    function getEnv(name: string): string {
      const value = process.env[name]
      if (!value) throw new Error(`Missing required env var: ${name}`)
      return value
    }

    const lambdaDefaultEnvironmentVariables: {[key: string]: string} = {
      SLACK_SLASH_COMMAND: getEnv("SLACK_SLASH_COMMAND"),
      KNOWLEDGEBASE_ID: "REPLACEME",
      RAG_MODEL_ID: getEnv("RAG_MODEL_ID"),
      GUARD_RAIL_ID: getEnv("GUARD_RAIL_ID"),
      GUARD_RAIL_VERSION: getEnv("GUARD_RAIL_VERSION"),
      SLACK_BOT_TOKEN_PARAMETER: getEnv("SLACK_BOT_TOKEN_PARAMETER"),
      SLACK_SIGNING_SECRET_PARAMETER: getEnv("SLACK_SIGNING_SECRET_PARAMETER")
    }

    // Python Lambda for SlackBot
    const slackBotLambda = new LambdaFunction(this, "SlackBotLambda", {
      stackName: "eps-assist-me",
      functionName: "SlackBotFunction",
      packageBasePath: "packages/slackBotFunction",
      entryPoint: "app.py",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      environmentVariables: lambdaDefaultEnvironmentVariables,
      additionalPolicies: []
    })

    // Create Guardrail
    const guardrail = new bedrock.Guardrail(this, "EpsGuardrail", {
      name: "eps-assist-guardrail",
      description: "Protects against unsafe input/output"
    })

    // Create Vector Knowledge Base
    const knowledgeBase = new bedrock.VectorKnowledgeBase(this, "EpsKb", {
      embeddingsModel: bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_1024,
      instruction: "Use this KB to answer questions about EPS."
    })

    new bedrock.S3DataSource(this, "EpsKbDataSource", {
      bucket: kbDocsBucket,
      knowledgeBase: knowledgeBase,
      dataSourceName: "eps-docs",
      chunkingStrategy: bedrock.ChunkingStrategy.fixedSize({maxTokens: 500, overlapPercentage: 10})
    })

    // API Endpoint
    const slackResource = apiGateway.api.root.addResource("slack").addResource("ask-eps")
    slackResource.addMethod("POST", new LambdaIntegration(slackBotLambda.function, {
      credentialsRole: apiGateway.role
    }))
    apiGateway.role.addManagedPolicy(slackBotLambda.executionPolicy)

    new CfnOutput(this, "SlackBotEndpoint", {
      value: `https://${apiGateway.api.domainName?.domainName}/slack/ask-eps`
    })

    // CDK Nag Suppressions
    nagSuppressions(this)
  }
}
