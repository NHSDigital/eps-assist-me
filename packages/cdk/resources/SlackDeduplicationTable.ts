import {Construct} from "constructs"
import {RemovalPolicy} from "aws-cdk-lib"
import {Table, AttributeType, BillingMode} from "aws-cdk-lib/aws-dynamodb"

export interface SlackDeduplicationTableProps {
  readonly stackName: string
}

export class SlackDeduplicationTable extends Construct {
  public readonly table: Table

  constructor(scope: Construct, id: string, props: SlackDeduplicationTableProps) {
    super(scope, id)

    this.table = new Table(this, "Table", {
      tableName: `${props.stackName}-SlackDeduplication`,
      partitionKey: {
        name: "eventId",
        type: AttributeType.STRING
      },
      billingMode: BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: "ttl",
      pointInTimeRecovery: true,
      removalPolicy: RemovalPolicy.DESTROY
    })
  }
}
