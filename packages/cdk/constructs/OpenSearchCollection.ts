import {Construct} from "constructs"
import * as ops from "aws-cdk-lib/aws-opensearchserverless"

export interface OpenSearchCollectionProps {
  collectionName: string
  principals: Array<string>
}

export class OpenSearchCollection extends Construct {
  public readonly collection: ops.CfnCollection
  public readonly endpoint: string

  constructor(scope: Construct, id: string, props: OpenSearchCollectionProps) {
    super(scope, id)

    // Encryption policy for collection (AWS-owned key)
    const encryptionPolicy = new ops.CfnSecurityPolicy(this, "EncryptionPolicy", {
      name: `${props.collectionName}-encryption-policy`,
      type: "encryption",
      policy: JSON.stringify({
        Rules: [{ResourceType: "collection", Resource: [`collection/${props.collectionName}`]}],
        AWSOwnedKey: true
      })
    })

    // Network policy for public access (collection & dashboard)
    const networkPolicy = new ops.CfnSecurityPolicy(this, "NetworkPolicy", {
      name: `${props.collectionName}-network-policy`,
      type: "network",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: [`collection/${props.collectionName}`]},
          {ResourceType: "dashboard", Resource: [`collection/${props.collectionName}`]}
        ],
        AllowFromPublic: true
      }])
    })

    // OpenSearch collection (VECTORSEARCH type)
    this.collection = new ops.CfnCollection(this, "Collection", {
      name: props.collectionName,
      description: "EPS Assist Vector Store",
      type: "VECTORSEARCH"
    })

    // Ensure collection is created after policies
    this.collection.addDependency(encryptionPolicy)
    this.collection.addDependency(networkPolicy)

    // Access policy for principals (full access to collection & indexes)
    const accessPolicy = new ops.CfnAccessPolicy(this, "AccessPolicy", {
      name: `${props.collectionName}-access-policy`,
      type: "data",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: ["collection/*"], Permission: ["aoss:*"]},
          {ResourceType: "index", Resource: ["index/*/*"], Permission: ["aoss:*"]}
        ],
        Principal: props.principals
      }])
    })

    // Ensure access policy applies after collection creation
    this.collection.addDependency(accessPolicy)

    // Collection endpoint
    this.endpoint = `${this.collection.attrId}.${this.collection.stack.region}.aoss.amazonaws.com`
  }
}
