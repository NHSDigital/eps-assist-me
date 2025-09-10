import {Construct} from "constructs"
import {CfnCollection, CfnIndex} from "aws-cdk-lib/aws-opensearchserverless"

export interface VectorIndexProps {
  readonly indexName: string
  readonly collection: CfnCollection
  readonly endpoint: string
}

export class VectorIndex extends Construct {
  public readonly cfnIndex: CfnIndex

  constructor(scope: Construct, id: string, props: VectorIndexProps) {
    super(scope, id)

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
          index: false
        }
      }
    }

    const cfnIndex = new CfnIndex(this, "MyCfnIndex", {
      collectionEndpoint: props.endpoint,
      indexName: props.indexName,
      mappings: indexMapping,
      // the properties below are optional
      settings: {
        index: {
          knn: true,
          knnAlgoParamEfSearch: 512
        }
      }
    })

    // Ensure collection exists before creating index
    cfnIndex.node.addDependency(props.collection)
    this.cfnIndex = cfnIndex
  }
}
