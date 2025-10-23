import {Construct} from "constructs"
import {CfnIndex} from "aws-cdk-lib/aws-opensearchserverless"
import {VectorCollection} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/opensearchserverless"
import {RemovalPolicy} from "aws-cdk-lib"

export interface VectorIndexProps {
  readonly stackName: string
  readonly collection: VectorCollection
}

export class VectorIndex extends Construct {
  public readonly cfnIndex: CfnIndex
  public readonly indexName: string

  constructor(scope: Construct, id: string, props: VectorIndexProps) {
    super(scope, id)

    this.indexName = `${props.stackName}-index`

    const indexMapping: CfnIndex.MappingsProperty = {
      properties: {
        "bedrock-knowledge-base-default-vector": {
          type: "knn_vector",
          dimension: 1024,
          method: {
            name: "hnsw",
            engine: "faiss",
            parameters: {},
            spaceType: "l2"
          }
        },
        "AMAZON_BEDROCK_METADATA": {
          type: "text",
          index: false
        },
        "AMAZON_BEDROCK_TEXT_CHUNK": {
          type: "text",
          index: true
        },
        "id": {
          type: "text",
          index: true
        },
        "x-amz-bedrock-kb-data-source-id": {
          type: "text",
          index: true
        },
        "x-amz-bedrock-kb-source-uri": {
          type: "text",
          index: true
        }
      }
    }

    const cfnIndex = new CfnIndex(this, "MyCfnIndex", {
      collectionEndpoint: props.collection.collectionEndpoint, // Use L2 property
      indexName: this.indexName,
      mappings: indexMapping,
      settings: {
        index: {
          knn: true,
          knnAlgoParamEfSearch: 512
        }
      }
    })

    this.cfnIndex = cfnIndex

    this.cfnIndex.applyRemovalPolicy(RemovalPolicy.DESTROY)
  }
}
