import {Construct} from "constructs"
import {Role} from "aws-cdk-lib/aws-iam"
import {Bucket} from "aws-cdk-lib/aws-s3"
import * as bedrock from "aws-cdk-lib/aws-bedrock"
import {createHash} from "crypto"

export interface VectorKnowledgeBaseProps {
  embeddingsModel: string
  docsBucket: Bucket
  bedrockExecutionRole: Role
  collectionArn: string
  vectorIndexName: string
}

export class VectorKnowledgeBaseResources extends Construct {
  public readonly knowledgeBase: bedrock.CfnKnowledgeBase
  public readonly guardrail: bedrock.CfnGuardrail

  constructor(scope: Construct, id: string, props: VectorKnowledgeBaseProps) {
    super(scope, id)

    this.guardrail = new bedrock.CfnGuardrail(this, "Guardrail", {
      name: `eps-assist-guardrail-${createHash("md5").update(this.node.addr).digest("hex").substring(0, 8)}`,
      description: "Guardrail for EPS Assist Me Slackbot",
      blockedInputMessaging: "Your input was blocked.",
      blockedOutputsMessaging: "Your output was blocked.",
      contentPolicyConfig: {
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
        piiEntitiesConfig: [
          {type: "EMAIL", action: "ANONYMIZE"},
          {type: "PHONE", action: "ANONYMIZE"},
          {type: "NAME", action: "ANONYMIZE"},
          {type: "CREDIT_DEBIT_CARD_NUMBER", action: "BLOCK"}
        ]
      },
      wordPolicyConfig: {
        managedWordListsConfig: [{type: "PROFANITY"}]
      }
    })

    this.knowledgeBase = new bedrock.CfnKnowledgeBase(this, "VectorKB", {
      name: `eps-assist-kb-${createHash("md5").update(this.node.addr).digest("hex").substring(0, 8)}`,
      description: "Knowledge base for EPS Assist Me Slackbot",
      roleArn: props.bedrockExecutionRole.roleArn,
      knowledgeBaseConfiguration: {
        type: "VECTOR",
        vectorKnowledgeBaseConfiguration: {
          embeddingModelArn: `arn:aws:bedrock:eu-west-2::foundation-model/${props.embeddingsModel}`
        }
      },
      storageConfiguration: {
        type: "OPENSEARCH_SERVERLESS",
        opensearchServerlessConfiguration: {
          collectionArn: props.collectionArn,
          vectorIndexName: props.vectorIndexName,
          fieldMapping: {
            vectorField: "bedrock-knowledge-base-default-vector",
            textField: "AMAZON_BEDROCK_TEXT_CHUNK",
            metadataField: "AMAZON_BEDROCK_METADATA"
          }
        }
      }
    })

    new bedrock.CfnDataSource(this, "S3DataSource", {
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
