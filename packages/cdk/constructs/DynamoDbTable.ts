import {Construct} from "constructs"
import {RemovalPolicy} from "aws-cdk-lib"
import {
  AttributeType,
  Billing,
  ProjectionType,
  TableEncryptionV2,
  TableV2
} from "aws-cdk-lib/aws-dynamodb"
import {Key} from "aws-cdk-lib/aws-kms"

export interface DynamoDbTableProps {
  readonly tableName: string
  readonly kmsKey: Key
}

export class DynamoDbTable extends Construct {
  public readonly table: TableV2

  constructor(scope: Construct, id: string, props: DynamoDbTableProps) {
    super(scope, id)

    this.table = new TableV2(this, props.tableName, {
      tableName: props.tableName,
      partitionKey: {
        name: "pk",
        type: AttributeType.STRING
      },
      sortKey: {
        name: "sk",
        type: AttributeType.STRING
      },
      billing: Billing.onDemand(),
      encryption: TableEncryptionV2.customerManagedKey(props.kmsKey),
      removalPolicy: RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true
      },
      // TODO: discuss TTL settings
      timeToLiveAttribute: "ttl"
    })

    // GSI for reverse lookups if needed (session_id -> thread info)
    this.table.addGlobalSecondaryIndex({
      indexName: "session-index",
      partitionKey: {
        name: "session_id",
        type: AttributeType.STRING
      },
      projectionType: ProjectionType.ALL
    })
  }
}
