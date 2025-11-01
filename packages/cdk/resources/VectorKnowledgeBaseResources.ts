import {Construct} from "constructs"
import {Role} from "aws-cdk-lib/aws-iam"
import {Bucket} from "aws-cdk-lib/aws-s3"
import {CfnKnowledgeBase, CfnDataSource} from "aws-cdk-lib/aws-bedrock"
import {
  ContentFilterStrength,
  ContentFilterType,
  Guardrail,
  GuardrailAction,
  ManagedWordFilterType,
  PIIType
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock"
import {RemovalPolicy} from "aws-cdk-lib"

// Amazon Titan embedding model for vector generation
const EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"

export interface VectorKnowledgeBaseProps {
  readonly stackName: string
  readonly docsBucket: Bucket
  readonly bedrockExecutionRole: Role
  readonly collectionArn: string
  readonly vectorIndexName: string
  readonly region: string
  readonly account: string
}

export class VectorKnowledgeBaseResources extends Construct {
  public readonly knowledgeBase: CfnKnowledgeBase
  public readonly guardrail: Guardrail
  public readonly dataSource: CfnDataSource
  private readonly region: string
  private readonly account: string

  public get dataSourceArn(): string {
    return `arn:aws:bedrock:${this.region}:${this.account}:knowledge-base/` +
      `${this.knowledgeBase.attrKnowledgeBaseId}/data-source/` +
      `${this.dataSource.attrDataSourceId}`
  }

  constructor(scope: Construct, id: string, props: VectorKnowledgeBaseProps) {
    super(scope, id)

    this.region = props.region
    this.account = props.account

    const guardrail = new Guardrail(this, "bedrockGuardrails", {
      name: `${props.stackName}-guardrail`,
      description: "Guardrail for EPS Assist Me Slackbot",
      blockedInputMessaging: "Your input was blocked.",
      blockedOutputsMessaging: "Your output was blocked.",
      contentFilters: [
        {
          type: ContentFilterType.SEXUAL,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.VIOLENCE,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.HATE,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.INSULTS,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.MISCONDUCT,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.PROMPT_ATTACK,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.NONE
        }
      ],
      piiFilters: [
        {
          type: PIIType.General.EMAIL,
          action: GuardrailAction.ANONYMIZE
        },
        {
          type: PIIType.General.PHONE,
          action: GuardrailAction.ANONYMIZE
        },
        {
          type: PIIType.General.NAME,
          action: GuardrailAction.ANONYMIZE
        },
        {
          type: PIIType.Finance.CREDIT_DEBIT_CARD_NUMBER,
          action: GuardrailAction.BLOCK
        },
        {
          type: PIIType.UKSpecific.UK_NATIONAL_HEALTH_SERVICE_NUMBER,
          action: GuardrailAction.ANONYMIZE
        }
      ],
      managedWordListFilters: [
        {type: ManagedWordFilterType.PROFANITY}
      ]
    })

    // Create vector knowledge base for document retrieval
    const knowledgeBase = new CfnKnowledgeBase(this, "VectorKB", {
      name: `${props.stackName}-kb`,
      description: "Knowledge base for EPS Assist Me Slackbot",
      roleArn: props.bedrockExecutionRole.roleArn,
      knowledgeBaseConfiguration: {
        type: "VECTOR",
        vectorKnowledgeBaseConfiguration: {
          embeddingModelArn: `arn:aws:bedrock:eu-west-2::foundation-model/${EMBEDDING_MODEL}`
        }
      },
      // Configure OpenSearch Serverless as vector store
      storageConfiguration: {
        type: "OPENSEARCH_SERVERLESS",
        opensearchServerlessConfiguration: {
          collectionArn: props.collectionArn,
          vectorIndexName: props.vectorIndexName,
          // Standard Bedrock field mappings for vector search
          fieldMapping: {
            vectorField: "bedrock-knowledge-base-default-vector",
            textField: "AMAZON_BEDROCK_TEXT_CHUNK",
            metadataField: "AMAZON_BEDROCK_METADATA"
          }
        }
      }
    })

    knowledgeBase.applyRemovalPolicy(RemovalPolicy.DESTROY)

    // Create S3 data source for knowledge base documents
    const dataSource = new CfnDataSource(this, "S3DataSource", {
      knowledgeBaseId: knowledgeBase.attrKnowledgeBaseId,
      name: `${props.stackName}-s3-datasource`,
      dataSourceConfiguration: {
        type: "S3",
        s3Configuration: {
          bucketArn: props.docsBucket.bucketArn
        }
      }
    })

    this.knowledgeBase = knowledgeBase
    this.dataSource = dataSource
    this.guardrail = guardrail
  }
}
