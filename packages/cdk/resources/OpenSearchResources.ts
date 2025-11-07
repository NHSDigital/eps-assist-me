import {Construct} from "constructs"
import {Role} from "aws-cdk-lib/aws-iam"
import {Tags} from "aws-cdk-lib"
import {
  VectorCollection,
  VectorCollectionStandbyReplicas
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/opensearchserverless"

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
      description: "EPS Assist Vector Store",
      standbyReplicas: VectorCollectionStandbyReplicas.DISABLED
    })

    // set static values for commit and version tags to stop it being recreated
    Tags.of(this.collection).add("commit", "static_value")
    Tags.of(this.collection).add("version", "static_value")

    // Grant access to the Bedrock execution role
    this.collection.grantDataAccess(props.bedrockExecutionRole)

  }
}
