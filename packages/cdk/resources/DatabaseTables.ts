import {Construct} from "constructs"
import {AttributeType} from "aws-cdk-lib/aws-dynamodb"
import {DynamoDbTable} from "../constructs/DynamoDbTable"

export interface TablesProps {
  readonly stackName: string
}

export class DatabaseTables extends Construct {
  public readonly slackBotStateTable: DynamoDbTable

  constructor(scope: Construct, id: string, props: TablesProps) {
    super(scope, id)

    this.slackBotStateTable = new DynamoDbTable(this, "SlackBotStateTable", {
      tableName: `${props.stackName}-SlackBotState`,
      partitionKey: {
        name: "eventId",
        type: AttributeType.STRING
      },
      timeToLiveAttribute: "ttl"
    })
  }
}
