import {Construct} from "constructs"
import {Role} from "aws-cdk-lib/aws-iam"
import {
  VectorCollection,
  VectorCollectionStandbyReplicas
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/opensearchserverless"
import {RemovalPolicy} from "aws-cdk-lib"

export interface OpenSearchResourcesProps {
  readonly stackName: string
  readonly bedrockExecutionRole: Role
  readonly region: string
}

export class OpenSearchResources extends Construct {
  public readonly collection: VectorCollection

  constructor(scope: Construct, id: string, props: OpenSearchResourcesProps) {
    super(scope, id)

    // Create the OpenSearch Serverless collection using L2 construct
    this.collection = new VectorCollection(this, "Collection", {
      collectionName: `${props.stackName}-vector-db`,
      description: "EPS Assist Vector Store",
      standbyReplicas: VectorCollectionStandbyReplicas.DISABLED
    })

    // Grant access to the Bedrock execution role
    this.collection.grantDataAccess(props.bedrockExecutionRole)

    this.collection.applyRemovalPolicy(RemovalPolicy.DESTROY)

  }
}
