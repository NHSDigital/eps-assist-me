import {Construct} from "constructs"
import {OpenSearchCollection} from "../constructs/OpenSearchCollection"
import * as iam from "aws-cdk-lib/aws-iam"
import {createHash} from "crypto"

export interface OpenSearchResourcesProps {
  bedrockExecutionRole: iam.Role
  createIndexFunctionRole: iam.Role
  account: string
}

export class OpenSearchResources extends Construct {
  public readonly collection: OpenSearchCollection

  constructor(scope: Construct, id: string, props: OpenSearchResourcesProps) {
    super(scope, id)

    this.collection = new OpenSearchCollection(this, "OsCollection", {
      // eps-assist-vector-db
      collectionName: `eps-vec-db-${createHash("md5").update(this.node.addr).digest("hex").substring(0, 8)}`,
      principals: [
        props.bedrockExecutionRole.roleArn,
        props.createIndexFunctionRole.roleArn,
        `arn:aws:iam::${props.account}:root`
      ]
    })
  }
}
