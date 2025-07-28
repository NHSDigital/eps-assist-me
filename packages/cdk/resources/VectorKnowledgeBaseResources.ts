import {Construct} from "constructs"
import {Role} from "aws-cdk-lib/aws-iam"
import {Bucket} from "aws-cdk-lib/aws-s3"
import {CfnKnowledgeBase, CfnGuardrail, CfnDataSource} from "aws-cdk-lib/aws-bedrock"
import {createHash} from "crypto"

// Amazon Titan embedding model for vector generation
const EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"

export interface VectorKnowledgeBaseProps {
  docsBucket: Bucket
  bedrockExecutionRole: Role
  collectionArn: string
  vectorIndexName: string
}

export class VectorKnowledgeBaseResources extends Construct {
  public readonly knowledgeBase: CfnKnowledgeBase
  public readonly guardrail: CfnGuardrail

  constructor(scope: Construct, id: string, props: VectorKnowledgeBaseProps) {
    super(scope, id)

    // Create Bedrock guardrail for content filtering
    this.guardrail = new CfnGuardrail(this, "Guardrail", {
      name: `eps-assist-guardrail-${createHash("md5").update(this.node.addr).digest("hex").substring(0, 8)}`,
      description: "Guardrail for EPS Assist Me Slackbot",
      blockedInputMessaging: "Your input was blocked.",
      blockedOutputsMessaging: "Your output was blocked.",
      contentPolicyConfig: {
        // Content filters for harmful content
        filtersConfig: [
          {type: "SEXUAL", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "VIOLENCE", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "HATE", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "INSULTS", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "MISCONDUCT", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "PROMPT_ATTACK", inputStrength: "HIGH", outputStrength: "NONE"}
        ]
      },
      sensitiveInformationPolicyConfig: {
        // PII detection and handling
        piiEntitiesConfig: [
          {type: "EMAIL", action: "ANONYMIZE"},
          {type: "PHONE", action: "ANONYMIZE"},
          {type: "NAME", action: "ANONYMIZE"},
          {type: "CREDIT_DEBIT_CARD_NUMBER", action: "BLOCK"}
        ]
      },
      wordPolicyConfig: {
        // Block profanity using AWS managed word lists
        managedWordListsConfig: [{type: "PROFANITY"}]
      }
    })

    // Create vector knowledge base for document retrieval
    this.knowledgeBase = new CfnKnowledgeBase(this, "VectorKB", {
      name: `eps-assist-kb-${createHash("md5").update(this.node.addr).digest("hex").substring(0, 8)}`,
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

    // Create S3 data source for knowledge base documents
    new CfnDataSource(this, "S3DataSource", {
      knowledgeBaseId: this.knowledgeBase.attrKnowledgeBaseId,
      name: `eps-assist-s3-datasource-${createHash("md5").update(this.node.addr).digest("hex").substring(0, 8)}`,
      dataSourceConfiguration: {
        type: "S3",
        s3Configuration: {
          bucketArn: props.docsBucket.bucketArn
        }
      }
    })
  }
}
