import {Construct} from "constructs"
import {AttributeType} from "aws-cdk-lib/aws-dynamodb"
import {DynamoDbTable} from "../constructs/DynamoDbTable"

export interface TablesProps {
  readonly stackName: string
}

export class DatabaseTables extends Construct {
  public readonly slackDeduplicationTable: DynamoDbTable

  constructor(scope: Construct, id: string, props: TablesProps) {
    super(scope, id)

    this.slackDeduplicationTable = new DynamoDbTable(this, "SlackDeduplicationTable", {
      tableName: `${props.stackName}-SlackDeduplication`,
      partitionKey: {
        name: "eventId",
        type: AttributeType.STRING
      },
      timeToLiveAttribute: "ttl"
    })
  }
}
