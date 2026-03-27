import {Construct} from "constructs"
import {AttributeType} from "aws-cdk-lib/aws-dynamodb"
import {DynamoDbTable} from "../constructs/DynamoDbTable"

export interface TablesProps {
  readonly stackName: string
}

export class DatabaseTables extends Construct {
  public readonly slackBotStateTable: DynamoDbTable
  public readonly knowledgeSyncStateTable: DynamoDbTable

  constructor(scope: Construct, id: string, props: TablesProps) {
    super(scope, id)

    this.slackBotStateTable = new DynamoDbTable(this, "SlackBotStateTable", {
      tableName: `${props.stackName}-SlackBotState`,
      partitionKey: {
        name: "pk",
        type: AttributeType.STRING
      },
      sortKey: {
        name: "sk",
        type: AttributeType.STRING
      },
      timeToLiveAttribute: "ttl"
    })

    this.knowledgeSyncStateTable = new DynamoDbTable(this, "KnowledgeSyncStateTable", {
      tableName: `${props.stackName}-KnowledgeSyncState`,
      partitionKey: {
        name: "user_channel_composite",
        type: AttributeType.STRING
      },
      sortKey: {
        name: "last_ts",
        type: AttributeType.STRING
      },
      timeToLiveAttribute: "ttl"
    })
  }
}
