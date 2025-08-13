import {Construct} from "constructs"
import {RemovalPolicy} from "aws-cdk-lib"
import {TableV2, AttributeType, Billing} from "aws-cdk-lib/aws-dynamodb"

export interface DynamoDbTableProps {
  readonly tableName: string
  readonly partitionKey: {
    name: string
    type: AttributeType
  }
  readonly timeToLiveAttribute?: string
}

export class DynamoDbTable extends Construct {
  public readonly table: TableV2

  constructor(scope: Construct, id: string, props: DynamoDbTableProps) {
    super(scope, id)

    this.table = new TableV2(this, props.tableName, {
      tableName: props.tableName,
      partitionKey: props.partitionKey,
      billing: Billing.onDemand(),
      timeToLiveAttribute: props.timeToLiveAttribute,
      pointInTimeRecovery: true,
      removalPolicy: RemovalPolicy.DESTROY
    })
  }
}
