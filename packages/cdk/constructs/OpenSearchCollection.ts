import {Construct} from "constructs"
import {Tags} from "aws-cdk-lib"
import {Role} from "aws-cdk-lib/aws-iam"
import {
  VectorCollection,
  VectorCollectionStandbyReplicas
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/opensearchserverless"
import {
  VectorIndex,
  MetadataManagementFieldProps
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/opensearch-vectorindex"
import {CfnCollection} from "aws-cdk-lib/aws-opensearchserverless"

export interface OpenSearchCollectionProps {
  readonly collectionName: string
  readonly principals: Array<string>
  readonly region: string
  readonly account: string
}

export class OpenSearchCollection extends Construct {
  public readonly vectorCollection: VectorCollection
  public readonly vectorIndex: VectorIndex
  public readonly endpoint: string

  // Maintain compatibility with existing interface
  public readonly collection: CfnCollection
  private readonly region: string
  private readonly account: string

  public get collectionArn(): string {
    return this.vectorCollection.collectionArn
  }

  constructor(scope: Construct, id: string, props: OpenSearchCollectionProps) {
    super(scope, id)

    this.region = props.region
    this.account = props.account

    // Use the higher-level construct that handles policies automatically
    this.vectorCollection = new VectorCollection(this, "Collection", {
      collectionName: props.collectionName,
      description: "EPS Assist Vector Store",
      standbyReplicas: VectorCollectionStandbyReplicas.DISABLED
    })

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
      collection: this.vectorCollection,
      indexName: "eps-assist-os-index",
      vectorField: "bedrock-knowledge-base-default-vector",
      vectorDimensions: 1024,
      precision: "float",
      distanceType: "cosine",
      mappings: mappings
    })

    // Grant access to the specified principals
    props.principals.forEach((principalArn, index) => {
      const role = Role.fromRoleArn(this, `ImportedRole${index}`, principalArn)
      this.vectorCollection.grantDataAccess(role)
    })

    // Access the underlying CfnCollection for compatibility
    this.collection = this.vectorCollection.node.findChild("VectorCollection") as CfnCollection

    // Set static values for commit and version tags
    Tags.of(this.vectorCollection).add("commit", "static_value")
    Tags.of(this.vectorCollection).add("version", "static_value")

    this.endpoint = this.vectorCollection.collectionEndpoint
  }
}
