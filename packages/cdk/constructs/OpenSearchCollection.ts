import {Construct} from "constructs"
import {CfnCollection, CfnSecurityPolicy, CfnAccessPolicy} from "aws-cdk-lib/aws-opensearchserverless"

export interface OpenSearchCollectionProps {
  collectionName: string
  principals: Array<string>
}

export class OpenSearchCollection extends Construct {
  public readonly collection: CfnCollection
  public readonly endpoint: string

  constructor(scope: Construct, id: string, props: OpenSearchCollectionProps) {
    super(scope, id)

    // Encryption policy using AWS-managed keys
    const encryptionPolicy = new CfnSecurityPolicy(this, "EncryptionPolicy", {
      name: `${props.collectionName}-encrypt-pr`,
      type: "encryption",
      policy: JSON.stringify({
        Rules: [{ResourceType: "collection", Resource: [`collection/${props.collectionName}`]}],
        AWSOwnedKey: true
      })
    })

    // Network policy allowing public internet access
    const networkPolicy = new CfnSecurityPolicy(this, "NetworkPolicy", {
      name: `${props.collectionName}-net-pr`,
      type: "network",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: [`collection/${props.collectionName}`]},
          {ResourceType: "dashboard", Resource: [`collection/${props.collectionName}`]}
        ],
        AllowFromPublic: true
      }])
    })

    // Data access policy granting full permissions to specified principals
    const accessPolicy = new CfnAccessPolicy(this, "AccessPolicy", {
      name: `${props.collectionName}-access-pr`,
      type: "data",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: ["collection/*"], Permission: ["aoss:*"]},
          {ResourceType: "index", Resource: ["index/*/*"], Permission: ["aoss:*"]}
        ],
        Principal: props.principals
      }])
    })

    // Vector search collection for document embeddings
    this.collection = new CfnCollection(this, "Collection", {
      name: props.collectionName,
      description: "EPS Assist Vector Store",
      type: "VECTORSEARCH"
    })

    // Ensure collection waits for all policies
    this.collection.addDependency(encryptionPolicy)
    this.collection.addDependency(networkPolicy)
    this.collection.addDependency(accessPolicy)

    this.endpoint = `${this.collection.attrId}.${this.collection.stack.region}.aoss.amazonaws.com`
  }
}
