import {Construct} from "constructs"
import {CfnCollection, CfnIndex} from "aws-cdk-lib/aws-opensearchserverless"
import {CustomResource} from "aws-cdk-lib"
import {ManagedPolicy, PolicyStatement} from "aws-cdk-lib/aws-iam"
import {Provider} from "aws-cdk-lib/custom-resources"
import {LambdaFunction} from "../constructs/LambdaFunction"

export interface VectorIndexProps {
  readonly indexName: string
  readonly collection: CfnCollection
  readonly endpoint: string
  readonly account: string
  readonly region: string
  readonly stackName: string
  readonly logRetentionInDays: number
  readonly logLevel: string
}

export class VectorIndex extends Construct {
  public readonly cfnIndex: CfnIndex
  public readonly indexReady: CustomResource

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

    //const collectionArn = `arn:aws:aoss:${props.region}:${props.account}:collection/${props.collection.name}`
    // eslint-disable-next-line max-len
    // const indexArn = `arn:aws:aoss:${props.region}:${props.account}:index/${props.collection.name}/${props.indexName}`

    //const collectionArn = "aoss:collection/*"
    const indexArn = `arn:aws:aoss:${props.region}:${props.account}:collection/${props.collection.attrId}`
    const getCollectionPolicy = new PolicyStatement({
      actions: [
        "aoss:BatchGetCollection"
      ],
      resources: ["*"]
    })
    const getIndexPolicy = new PolicyStatement({
      actions: [
        "aoss:GetIndex"
      ],
      resources: [indexArn]
    })
    const waiterFnManagedPolicy = new ManagedPolicy(this, "waiterFnManagedPolicy", {
      description: "Policy for Bedrock Knowledge Base to access S3 and OpenSearch",
      statements: [
        getCollectionPolicy,
        getIndexPolicy
      ]
    })

    const waiterFn = new LambdaFunction(this, "waiterLambda", {
      stackName: props.stackName,
      functionName: `${props.stackName}-VectorIndexWaiter`,
      packageBasePath: "packages/indexWaiter",
      handler: "index_waiter.handler",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      additionalPolicies: [waiterFnManagedPolicy]
    })

    const provider = new Provider(this, "IndexWaiterProvider", {
      onEventHandler: waiterFn.function
    })

    const indexReady = new CustomResource(this, "IndexReady", {
      serviceToken: provider.serviceToken,
      properties: {
        Endpoint: props.endpoint,
        IndexName: props.indexName
      }
    })
    // Ensure collection exists before creating index
    cfnIndex.node.addDependency(props.collection)
    indexReady.node.addDependency(props.collection)
    indexReady.node.addDependency(cfnIndex)

    this.cfnIndex = cfnIndex
    this.indexReady = indexReady
  }
}
