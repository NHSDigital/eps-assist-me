import {Construct} from "constructs"
import {CfnKnowledgeBase, CfnDataSource} from "aws-cdk-lib/aws-bedrock"
import * as iam from "aws-cdk-lib/aws-iam"
import * as ops from "aws-cdk-lib/aws-opensearchserverless"
import {Bucket} from "aws-cdk-lib/aws-s3"
import {BedrockGuardrail} from "../constructs/BedrockGuardrail"

const EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
const VECTOR_INDEX_NAME = "eps-assist-os-index"
const BEDROCK_KB_NAME = "eps-assist-kb"

export interface BedrockResourcesProps {
  bedrockExecutionRole: iam.Role
  osCollection: ops.CfnCollection
  kbDocsBucket: Bucket
  region: string
}

export class BedrockResources extends Construct {
  public readonly guardrail: BedrockGuardrail
  public readonly knowledgeBase: CfnKnowledgeBase
  public readonly dataSource: CfnDataSource

  constructor(scope: Construct, id: string, props: BedrockResourcesProps) {
    super(scope, id)

    this.guardrail = new BedrockGuardrail(this, "EpsGuardrail", {
      name: "eps-assist-guardrail",
      description: "Guardrail for EPS Assist Me bot"
    })

    this.knowledgeBase = new CfnKnowledgeBase(this, "EpsKb", {
      name: BEDROCK_KB_NAME,
      description: "EPS Assist Knowledge Base",
      roleArn: props.bedrockExecutionRole.roleArn,
      knowledgeBaseConfiguration: {
        type: "VECTOR",
        vectorKnowledgeBaseConfiguration: {
          embeddingModelArn: `arn:aws:bedrock:${props.region}::foundation-model/${EMBEDDING_MODEL}`
        }
      },
      storageConfiguration: {
        type: "OPENSEARCH_SERVERLESS",
        opensearchServerlessConfiguration: {
          collectionArn: props.osCollection.attrArn,
          fieldMapping: {
            vectorField: "bedrock-knowledge-base-default-vector",
            textField: "AMAZON_BEDROCK_TEXT_CHUNK",
            metadataField: "AMAZON_BEDROCK_METADATA"
          },
          vectorIndexName: VECTOR_INDEX_NAME
        }
      }
    })

    this.dataSource = new CfnDataSource(this, "EpsKbDataSource", {
      name: "eps-assist-kb-ds",
      knowledgeBaseId: this.knowledgeBase.attrKnowledgeBaseId,
      dataSourceConfiguration: {
        type: "S3",
        s3Configuration: {
          bucketArn: props.kbDocsBucket.bucketArn
        }
      }
    })
  }
}
