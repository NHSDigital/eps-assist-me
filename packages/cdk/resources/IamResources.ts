import {Construct} from "constructs"
import {
  PolicyStatement,
  Role,
  ServicePrincipal,
  ManagedPolicy
} from "aws-cdk-lib/aws-iam"
import {Bucket} from "aws-cdk-lib/aws-s3"

// Amazon Titan embedding model for vector generation
const EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
// Claude model for RAG responses
const RAG_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
// Claude model for query reformulation
const QUERY_REFORMULATION_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

export interface IamResourcesProps {
  readonly region: string
  readonly account: string
  readonly kbDocsBucket: Bucket
  readonly slackBotTokenParameterName: string
  readonly slackSigningSecretParameterName: string
  readonly slackBotStateTableArn: string
  readonly slackBotStateTableKmsKeyArn: string
}

export class IamResources extends Construct {
  public readonly bedrockExecutionRole: Role
  public readonly createIndexManagedPolicy: ManagedPolicy
  public readonly slackBotManagedPolicy: ManagedPolicy

  constructor(scope: Construct, id: string, props: IamResourcesProps) {
    super(scope, id)

    // Create Bedrock execution role policies for embedding model access
    const bedrockExecutionRolePolicy = new PolicyStatement({
      actions: ["bedrock:InvokeModel"],
      resources: [`arn:aws:bedrock:${props.region}::foundation-model/${EMBEDDING_MODEL}`]
    })

    // Policy for Bedrock Knowledge Base deletion operations
    const bedrockKBDeleteRolePolicy = new PolicyStatement({
      actions: ["bedrock:Delete*"],
      resources: [`arn:aws:bedrock:${props.region}:${props.account}:knowledge-base/*`]
    })

    // OpenSearch Serverless access policy for Knowledge Base operations
    const bedrockOSSPolicyForKnowledgeBase = new PolicyStatement({
      actions: [
        "aoss:APIAccessAll",
        "aoss:DeleteAccessPolicy",
        "aoss:DeleteCollection",
        "aoss:DeleteLifecyclePolicy",
        "aoss:DeleteSecurityConfig",
        "aoss:DeleteSecurityPolicy"
      ],
      resources: [`arn:aws:aoss:${props.region}:${props.account}:collection/*`]
    })

    // S3 bucket-specific access policies
    const s3AccessListPolicy = new PolicyStatement({
      actions: ["s3:ListBucket"],
      resources: [props.kbDocsBucket.bucketArn],
      conditions: {"StringEquals": {"aws:ResourceAccount": props.account}}
    })

    const s3AccessGetPolicy = new PolicyStatement({
      actions: ["s3:GetObject"],
      resources: [`${props.kbDocsBucket.bucketArn}/*`],
      conditions: {"StringEquals": {"aws:ResourceAccount": props.account}}
    })

    // KMS permissions for S3 bucket encryption
    const kmsAccessPolicy = new PolicyStatement({
      actions: ["kms:Decrypt", "kms:DescribeKey"],
      resources: ["*"],
      conditions: {"StringEquals": {"aws:ResourceAccount": props.account}}
    })

    // Create managed policy for Bedrock execution role
    const bedrockExecutionManagedPolicy = new ManagedPolicy(this, "BedrockExecutionManagedPolicy", {
      description: "Policy for Bedrock Knowledge Base to access S3 and OpenSearch",
      statements: [
        bedrockExecutionRolePolicy,
        bedrockKBDeleteRolePolicy,
        bedrockOSSPolicyForKnowledgeBase,
        s3AccessListPolicy,
        s3AccessGetPolicy,
        kmsAccessPolicy
      ]
    })

    // Create Bedrock execution role with managed policy
    this.bedrockExecutionRole = new Role(this, "EpsAssistMeBedrockExecutionRole", {
      assumedBy: new ServicePrincipal("bedrock.amazonaws.com"),
      description: "Role for Bedrock Knowledge Base to access S3 and OpenSearch",
      managedPolicies: [bedrockExecutionManagedPolicy]
    })

    // Create managed policy for CreateIndex Lambda function
    const createIndexPolicy = new PolicyStatement({
      actions: [
        "aoss:APIAccessAll",
        "aoss:DescribeIndex",
        "aoss:ReadDocument",
        "aoss:CreateIndex",
        "aoss:DeleteIndex",
        "aoss:UpdateIndex",
        "aoss:WriteDocument",
        "aoss:CreateCollectionItems",
        "aoss:DeleteCollectionItems",
        "aoss:UpdateCollectionItems",
        "aoss:DescribeCollectionItems"
      ],
      resources: [
        `arn:aws:aoss:${props.region}:${props.account}:collection/*`,
        `arn:aws:aoss:${props.region}:${props.account}:index/*`
      ]
    })

    this.createIndexManagedPolicy = new ManagedPolicy(this, "CreateIndexManagedPolicy", {
      description: "Policy for Lambda to create OpenSearch index",
      statements: [createIndexPolicy]
    })

    // Create managed policy for SlackBot Lambda function
    const slackBotPolicy = new PolicyStatement({
      actions: ["bedrock:InvokeModel"],
      resources: [`arn:aws:bedrock:${props.region}::foundation-model/${RAG_MODEL_ID}`]
    })

    const slackBotKnowledgeBasePolicy = new PolicyStatement({
      actions: ["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
      resources: [`arn:aws:bedrock:${props.region}:${props.account}:knowledge-base/*`]
    })

    const slackBotSSMPolicy = new PolicyStatement({
      actions: ["ssm:GetParameter"],
      resources: [
        `arn:aws:ssm:${props.region}:${props.account}:parameter${props.slackBotTokenParameterName}`,
        `arn:aws:ssm:${props.region}:${props.account}:parameter${props.slackSigningSecretParameterName}`
      ]
    })

    const slackBotLambdaPolicy = new PolicyStatement({
      actions: ["lambda:InvokeFunction"],
      resources: [`arn:aws:lambda:${props.region}:${props.account}:function:*`]
    })

    const slackBotGuardrailPolicy = new PolicyStatement({
      actions: ["bedrock:ApplyGuardrail"],
      resources: [`arn:aws:bedrock:${props.region}:${props.account}:guardrail/*`]
    })

    const slackBotQueryReformulationPolicy = new PolicyStatement({
      actions: ["bedrock:InvokeModel"],
      resources: [`arn:aws:bedrock:${props.region}::foundation-model/${QUERY_REFORMULATION_MODEL_ID}`]
    })

    const slackBotDynamoDbPolicy = new PolicyStatement({
      actions: [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:UpdateItem"
      ],
      resources: [props.slackBotStateTableArn]
    })

    const slackBotKmsPolicy = new PolicyStatement({
      actions: [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:DescribeKey"
      ],
      resources: [props.slackBotStateTableKmsKeyArn]
    })

    this.slackBotManagedPolicy = new ManagedPolicy(this, "SlackBotManagedPolicy", {
      description: "Policy for SlackBot Lambda to access Bedrock, SSM, Lambda, DynamoDB, and KMS",
      statements: [
        slackBotPolicy,
        slackBotKnowledgeBasePolicy,
        slackBotSSMPolicy,
        slackBotLambdaPolicy,
        slackBotGuardrailPolicy,
        slackBotQueryReformulationPolicy,
        slackBotDynamoDbPolicy,
        slackBotKmsPolicy
      ]
    })
  }
}
