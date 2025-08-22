import {Construct} from "constructs"
import {PolicyStatement, ManagedPolicy} from "aws-cdk-lib/aws-iam"

// Claude model for RAG responses
const RAG_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
// Claude model for query reformulation
const QUERY_REFORMULATION_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

export interface RuntimePoliciesProps {
  readonly region: string
  readonly account: string
  readonly slackBotTokenParameterName: string
  readonly slackSigningSecretParameterName: string
  readonly slackBotStateTableArn: string
  readonly slackBotStateTableKmsKeyArn: string
  readonly knowledgeBaseArn: string
  readonly guardrailArn: string
  readonly dataSourceArn: string
  readonly promptName: string
}

export class RuntimePolicies extends Construct {
  public readonly createIndexPolicy: ManagedPolicy
  public readonly slackBotPolicy: ManagedPolicy
  public readonly syncKnowledgeBasePolicy: ManagedPolicy

  constructor(scope: Construct, id: string, props: RuntimePoliciesProps) {
    super(scope, id)

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

    this.createIndexPolicy = new ManagedPolicy(this, "CreateIndexPolicy", {
      description: "Policy for Lambda to create OpenSearch index",
      statements: [createIndexPolicy]
    })

    // Create managed policy for SlackBot Lambda function
    const slackBotPolicy = new PolicyStatement({
      actions: ["bedrock:InvokeModel"],
      resources: [
        `arn:aws:bedrock:${props.region}::foundation-model/${RAG_MODEL_ID}`,
        `arn:aws:bedrock:${props.region}::foundation-model/${QUERY_REFORMULATION_MODEL_ID}`
      ]
    })

    const slackBotPromptPolicy = new PolicyStatement({
      actions: ["bedrock:GetPrompt"],
      resources: [
        `arn:aws:bedrock:${props.region}:${props.account}:prompt/${props.promptName}`,
        `arn:aws:bedrock:${props.region}:${props.account}:prompt/${props.promptName}:*`
      ]
    })

    const slackBotKnowledgeBasePolicy = new PolicyStatement({
      actions: ["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
      resources: [props.knowledgeBaseArn]
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
      resources: [props.guardrailArn]
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

    this.slackBotPolicy = new ManagedPolicy(this, "SlackBotPolicy", {
      description: "Policy for SlackBot Lambda to access Bedrock, SSM, Lambda, DynamoDB, and KMS",
      statements: [
        slackBotPolicy,
        slackBotPromptPolicy,
        slackBotKnowledgeBasePolicy,
        slackBotSSMPolicy,
        slackBotLambdaPolicy,
        slackBotGuardrailPolicy,
        slackBotDynamoDbPolicy,
        slackBotKmsPolicy
      ]
    })

    // Create managed policy for SyncKnowledgeBase Lambda function
    const syncKnowledgeBasePolicy = new PolicyStatement({
      actions: [
        "bedrock:StartIngestionJob",
        "bedrock:GetIngestionJob",
        "bedrock:ListIngestionJobs"
      ],
      resources: [
        props.knowledgeBaseArn,
        props.dataSourceArn
      ]
    })

    this.syncKnowledgeBasePolicy = new ManagedPolicy(this, "SyncKnowledgeBasePolicy", {
      description: "Policy for SyncKnowledgeBase Lambda to trigger ingestion jobs",
      statements: [syncKnowledgeBasePolicy]
    })
  }
}
