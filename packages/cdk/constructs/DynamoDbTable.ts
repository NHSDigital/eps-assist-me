import {Construct} from "constructs"
import {RemovalPolicy} from "aws-cdk-lib"
import {
  AttributeType,
  Billing,
  TableEncryptionV2,
  TableV2
} from "aws-cdk-lib/aws-dynamodb"
import {Key} from "aws-cdk-lib/aws-kms"

export interface DynamoDbTableProps {
  readonly tableName: string
  readonly partitionKey: {
    name: string
    type: AttributeType
  }
  readonly sortKey?: {
    name: string
    type: AttributeType
  }
  readonly timeToLiveAttribute?: string
}

export class DynamoDbTable extends Construct {
  public readonly table: TableV2
  public readonly kmsKey: Key

  constructor(scope: Construct, id: string, props: DynamoDbTableProps) {
    super(scope, id)

    // Use provided KMS key or create a new one
    this.kmsKey = new Key(this, "TableKey", {
      enableKeyRotation: true,
      description: `KMS key for ${props.tableName} DynamoDB table encryption`,
      removalPolicy: RemovalPolicy.DESTROY
    })

    this.kmsKey.addAlias(`alias/${props.tableName}-dynamodb-key`)

    this.table = new TableV2(this, props.tableName, {
      tableName: props.tableName,
      partitionKey: props.partitionKey,
      sortKey: props.sortKey,
      billing: Billing.onDemand(),
      timeToLiveAttribute: props.timeToLiveAttribute,
      pointInTimeRecovery: true,
      removalPolicy: RemovalPolicy.DESTROY,
      encryption: TableEncryptionV2.customerManagedKey(this.kmsKey)
    })
  }
}
