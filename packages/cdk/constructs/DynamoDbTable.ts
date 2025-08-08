import {Construct} from "constructs"
import {RemovalPolicy} from "aws-cdk-lib"
import {Table, AttributeType, BillingMode} from "aws-cdk-lib/aws-dynamodb"

export interface DynamoDbTableProps {
  readonly tableName: string
  readonly partitionKey: {
    name: string
    type: AttributeType
  }
  readonly timeToLiveAttribute?: string
}

export class DynamoDbTable extends Construct {
  public readonly table: Table

  constructor(scope: Construct, id: string, props: DynamoDbTableProps) {
    super(scope, id)

    this.table = new Table(this, props.tableName, {
      tableName: props.tableName,
      partitionKey: props.partitionKey,
      billingMode: BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: props.timeToLiveAttribute,
      pointInTimeRecovery: true,
      removalPolicy: RemovalPolicy.DESTROY
    })
  }
}
