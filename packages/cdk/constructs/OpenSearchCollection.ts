import {Construct} from "constructs"
import {CfnCollection, CfnSecurityPolicy, CfnAccessPolicy} from "aws-cdk-lib/aws-opensearchserverless"
import {Tags} from "aws-cdk-lib"

export interface OpenSearchCollectionProps {
  readonly collectionName: string
  readonly principals: Array<string>
  readonly region: string
  readonly account: string
}

export class OpenSearchCollection extends Construct {
  public readonly collection: CfnCollection
  public readonly endpoint: string
  private readonly region: string
  private readonly account: string

  public get collectionArn(): string {
    return `arn:aws:aoss:${this.region}:${this.account}:collection/${this.collection.attrId}`
  }

  constructor(scope: Construct, id: string, props: OpenSearchCollectionProps) {
    super(scope, id)

    this.region = props.region
    this.account = props.account

    // Encryption policy using AWS-managed keys
    const encryptionPolicy = new CfnSecurityPolicy(this, "EncryptionPolicy", {
      name: `${props.collectionName}-encryption`,
      type: "encryption",
      policy: JSON.stringify({
        Rules: [{ResourceType: "collection", Resource: [`collection/${props.collectionName}`]}],
        AWSOwnedKey: true
      })
    })

    // Network policy allowing public internet access
    const networkPolicy = new CfnSecurityPolicy(this, "NetworkPolicy", {
      name: `${props.collectionName}-network`,
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
      name: `${props.collectionName}-access`,
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
    // this can not be modified (including tags) so if we modify any properties
    // we should ensure the name is changed to ensure a new resource is created
    const collection = new CfnCollection(this, "Collection", {
      name: props.collectionName,
      description: "EPS Assist Vector Store",
      type: "VECTORSEARCH"
    })

    // set static values for commit and version tags to stop it being recreated
    Tags.of(collection).add("commit", "static_value")
    Tags.of(collection).add("version", "static_value")

    // Ensure collection waits for all policies
    collection.addDependency(encryptionPolicy)
    collection.addDependency(networkPolicy)
    collection.addDependency(accessPolicy)

    this.endpoint = `${collection.attrId}.${collection.stack.region}.aoss.amazonaws.com`
    this.collection = collection
  }
}
