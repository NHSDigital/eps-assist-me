import {Construct} from "constructs"
import {Role} from "aws-cdk-lib/aws-iam"
import {Tags} from "aws-cdk-lib"
import {
  VectorCollection,
  VectorCollectionStandbyReplicas
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/opensearchserverless"
import {
  VectorIndex,
  MetadataManagementFieldProps
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/opensearch-vectorindex"

export interface OpenSearchResourcesProps {
  readonly stackName: string
  readonly bedrockExecutionRole: Role
  readonly region: string
}

export class OpenSearchResources extends Construct {
  public readonly collection: VectorCollection
  public readonly vectorIndex: VectorIndex

  constructor(scope: Construct, id: string, props: OpenSearchResourcesProps) {
    super(scope, id)

    // Create the OpenSearch Serverless collection using L2 construct
    this.collection = new VectorCollection(this, "Collection", {
      collectionName: `${props.stackName}-vector-db`,
      description: "EPS Assist Vector Store",
      standbyReplicas: VectorCollectionStandbyReplicas.DISABLED // For cost optimization
    })

    // Grant access to the Bedrock execution role
    this.collection.grantDataAccess(props.bedrockExecutionRole)

    // Define the metadata mappings for Bedrock Knowledge Base compatibility
    const mappings: Array<MetadataManagementFieldProps> = [
      {
        mappingField: "AMAZON_BEDROCK_METADATA",
        dataType: "text",
        filterable: false
      },
      {
        mappingField: "AMAZON_BEDROCK_TEXT_CHUNK",
        dataType: "text",
        filterable: true
      },
      {
        mappingField: "id",
        dataType: "text",
        filterable: true
      },
      {
        mappingField: "x-amz-bedrock-kb-data-source-id",
        dataType: "text",
        filterable: true
      },
      {
        mappingField: "x-amz-bedrock-kb-source-uri",
        dataType: "text",
        filterable: true
      }
    ]

    // Create the vector index with Bedrock-compatible field mappings
    this.vectorIndex = new VectorIndex(this, "VectorIndex", {
      collection: this.collection,
      indexName: "eps-assist-os-index",
      vectorField: "bedrock-knowledge-base-default-vector",
      vectorDimensions: 1024,
      precision: "float",
      distanceType: "cosine",
      mappings: mappings
    })

    // Set static values for commit and version tags to prevent recreation
    Tags.of(this.collection).add("commit", "static_value")
    Tags.of(this.collection).add("version", "static_value")
  }
}
