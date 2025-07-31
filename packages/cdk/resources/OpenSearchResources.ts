import {Construct} from "constructs"
import {OpenSearchCollection} from "../constructs/OpenSearchCollection"
import {Role} from "aws-cdk-lib/aws-iam"

export interface OpenSearchResourcesProps {
  bedrockExecutionRole: Role
  account: string
}

export class OpenSearchResources extends Construct {
  public readonly collection: OpenSearchCollection

  constructor(scope: Construct, id: string, props: OpenSearchResourcesProps) {
    super(scope, id)

    // OpenSearch Serverless collection with vector search capabilities
    this.collection = new OpenSearchCollection(this, "OsCollection", {
      collectionName: "eps-assist-vector-db-foo",
      principals: [
        props.bedrockExecutionRole.roleArn, // Bedrock Knowledge Base access
        `arn:aws:iam::${props.account}:root` // Account root access
      ]
    })
  }
}
