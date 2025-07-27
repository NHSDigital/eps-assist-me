import {Construct} from "constructs"
import {OpenSearchCollection} from "../constructs/OpenSearchCollection"
import * as iam from "aws-cdk-lib/aws-iam"

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
      collectionName: `eps-vec-${this.node.addr}`, // eps-assist-vector-db
      principals: [
        props.bedrockExecutionRole.roleArn,
        props.createIndexFunctionRole.roleArn,
        `arn:aws:iam::${props.account}:root`
      ]
    })
  }
}
