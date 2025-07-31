import {Construct} from "constructs"
import {Duration} from "aws-cdk-lib"
import {CfnAccessPolicy, CfnIndex, CfnCollection} from "aws-cdk-lib/aws-opensearchserverless"

/**
 * The field data type. Must be a valid OpenSearch field type.
 */
export enum OpensearchFieldType {
  TEXT = "text",
  KNN_VECTOR = "knn_vector",
}

/**
 * The k-NN search engine to use.
 */
export enum EngineType {
  /**
   * C++ implementation.
   */
  FAISS = "faiss",
  /**
   * C++ implementation.
   */
  NMSLIB = "nmslib",
  /**
   * Java implementation.
   */
  LUCENE = "lucene",
}

/**
 * The algorithm name for k-NN search.
 */
export enum AlgorithmNameType {
  HNSW = "hnsw",
  IVF = "ivf",
}

/**
 * The distance function used for k-NN search.
 */
export enum SpaceType {
  L2 = "l2",
  L1 = "l1",
  LINF = "linf",
  COSINESIMILARITY = "cosinesimil",
  INNERPRODUCT = "innerproduct",
  HAMMING = "hamming",
}

/**
 * Additional parameters for the k-NN algorithm.
 */
export interface MethodParameters {
  /**
   * The size of the dynamic list used during k-NN graph creation.
   */
  readonly efConstruction?: number;
  /**
   * Number of neighbors to consider during k-NN search.
   */
  readonly m?: number;
}

/**
 * Configuration for k-NN search method.
 */
export interface Method {
  /**
   * The k-NN search engine to use.
  */
  readonly engine: EngineType;
  /**
   * The algorithm name for k-NN search.
   */
  readonly name: AlgorithmNameType;
  /**
   * Additional parameters for the k-NN algorithm.
   */
  readonly parameters?: MethodParameters;
  /**
   * The distance function used for k-NN search.
   */
  readonly spaceType?: SpaceType;
}

export interface PropertyMapping {
  /**
   * Dimension size for vector fields, defines the number of dimensions in the vector.
   */
  readonly dimension?: number;
  /**
   * Whether the index is indexed. Previously, this was called `filterable`.
   */
  readonly index?: boolean;
  /**
   * Configuration for k-NN search method.
   */
  readonly method?: Method;
  /**
   * Defines the fields within the mapping, including their types and configurations.
   */
  readonly properties?: Record<string, PropertyMapping>;
  /**
   * The field data type. Must be a valid OpenSearch field type.
   */
  readonly type: OpensearchFieldType;
  /**
   * Default value for the field when not specified in a document.
   */
  readonly value?: string;
}

/**
 * Index settings for the OpenSearch Serverless index.
 */
export interface IndexSettings {
  /**
   * Enable or disable k-nearest neighbor search capability.
   */
  readonly knn?: boolean;
  /**
   * The size of the dynamic list for the nearest neighbors.
   */
  readonly knnAlgoParamEfSearch?: number;
  /**
   * How often to perform a refresh operation. For example, 1s or 5s.
   */
  readonly refreshInterval?: Duration;
}

/**
 * The mappings for the OpenSearch Serverless index.
 */
export interface MappingsProperty {
  readonly properties: Record<string, PropertyMapping>;
}

export interface VectorIndexProps {
  readonly indexName: string
  readonly endpoint: string
  readonly mappings?: MappingsProperty
  readonly settings?: IndexSettings
  readonly collection: CfnCollection
}

export class VectorIndex extends Construct {
  public readonly vectorIndex: CfnIndex

  constructor(scope: Construct, id: string, props: VectorIndexProps) {
    super(scope, id)

    const manageIndexPolicy = new CfnAccessPolicy(
      this,
      "ManageIndexPolicy",
      {
        name: "foo",
        type: "data",
        policy: JSON.stringify([
          {
            Rules: [
              {
                Resource: [`index/${props.collection.name}/*`],
                Permission: [
                  "aoss:DescribeIndex",
                  "aoss:CreateIndex",
                  "aoss:DeleteIndex",
                  "aoss:UpdateIndex"
                ],
                ResourceType: "index"
              },
              {
                Resource: [`collection/${props.collection.name}`],
                Permission: ["aoss:DescribeCollectionItems"],
                ResourceType: "collection"
              }
            ],
            Principal: ["*"],
            Description: ""
          }
        ])
      }
    )
    this.vectorIndex = new CfnIndex(this, "VectorIndex", {
      indexName: props.indexName,
      collectionEndpoint: props.endpoint,
      mappings: this._renderMappings(props.mappings),
      settings: this._renderIndexSettings(props.settings)
    })

    // Ensure collection exists before creating index
    this.vectorIndex.node.addDependency(manageIndexPolicy)
    this.vectorIndex.node.addDependency(props.collection)
  }

  /**
   * Render the index settings.
   */
  private _renderIndexSettings(props?: IndexSettings): CfnIndex.IndexSettingsProperty {
    if (!props) return {}

    return {
      index: {
        knn: props?.knn,
        knnAlgoParamEfSearch: props?.knnAlgoParamEfSearch,
        refreshInterval: props?.refreshInterval?.toString()
      }
    }
  }

  /**
   * Render the mappings.
   */
  private _renderMappings(props?: MappingsProperty): CfnIndex.MappingsProperty {
    if (!props) return {}

    const convertedProps: Record<string, CfnIndex.PropertyMappingProperty> = {}
    for (const [key, value] of Object.entries(props.properties)) {
      convertedProps[key] = value as unknown as CfnIndex.PropertyMappingProperty
    }

    return {
      properties: convertedProps
    }
  }
}
