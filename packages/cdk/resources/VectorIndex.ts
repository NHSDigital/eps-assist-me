import {Construct} from "constructs"
import {CfnIndex} from "aws-cdk-lib/aws-opensearchserverless"
import {VectorCollection} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/opensearchserverless"
import {RemovalPolicy} from "aws-cdk-lib"
import {DelayResource} from "../constructs/DelayResource"

export interface VectorIndexProps {
  readonly stackName: string
  readonly collection: VectorCollection
}

export class VectorIndex extends Construct {
  public readonly cfnIndex: CfnIndex
  public readonly indexName: string
  public readonly policySyncWait: DelayResource
  public readonly indexReadyWait: DelayResource

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

    const cfnIndex = new CfnIndex(this, "OpenSearchIndex", {
      collectionEndpoint: props.collection.collectionEndpoint,
      indexName: this.indexName,
      mappings: indexMapping,
      settings: {
        index: {
          knn: true,
          knnAlgoParamEfSearch: 512
        }
      }
    })

    // a fix for an annoying time sync issue that adds a small delay
    // to ensure data access policies are synced before index creation
    const policySyncWait = new DelayResource(this, "PolicySyncWait", {
      delaySeconds: 60,
      description: "Wait for OpenSearch data access policies to sync",
      name: `${props.stackName}-policy-sync-wait`
    })

    policySyncWait.customResource.node.addDependency(props.collection.dataAccessPolicy)

    // Index depends on policy sync wait instead of directly on dataAccessPolicy
    cfnIndex.node.addDependency(policySyncWait.customResource)

    cfnIndex.applyRemovalPolicy(RemovalPolicy.DESTROY)

    // a fix for an annoying time sync issue that adds a small delay
    // to ensure index is actually available for Bedrock
    const indexReadyWait = new DelayResource(this, "IndexReadyWait", {
      delaySeconds: 60,
      description: "Wait for OpenSearch index to be fully available",
      name: `${props.stackName}-index-ready-wait`
    })

    indexReadyWait.customResource.node.addDependency(cfnIndex)

    this.cfnIndex = cfnIndex
    this.policySyncWait = policySyncWait
    this.indexReadyWait = indexReadyWait
  }
}
