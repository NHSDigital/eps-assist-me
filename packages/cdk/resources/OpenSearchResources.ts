import {Construct} from "constructs"
import {OpenSearchCollection} from "../constructs/OpenSearchCollection"
import {Role} from "aws-cdk-lib/aws-iam"
import {createHash} from "crypto"

export interface OpenSearchResourcesProps {
  bedrockExecutionRole: Role
  createIndexFunctionRole: Role
  account: string
}

export class OpenSearchResources extends Construct {
  public readonly collection: OpenSearchCollection

  constructor(scope: Construct, id: string, props: OpenSearchResourcesProps) {
    super(scope, id)

    // Create OpenSearch Serverless collection for vector storage
    this.collection = new OpenSearchCollection(this, "OsCollection", {
      // Generate unique collection name with hash suffix (eps-assist-vector-db)
      collectionName: `eps-vec-db-${createHash("md5").update(this.node.addr).digest("hex").substring(0, 8)}`,
      // Grant access to Bedrock, Lambda, and account root
      principals: [
        props.bedrockExecutionRole.roleArn,
        props.createIndexFunctionRole.roleArn,
        `arn:aws:iam::${props.account}:root`
      ]
    })
  }
}
