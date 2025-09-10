import {Construct} from "constructs"
import {AttributeType} from "aws-cdk-lib/aws-dynamodb"
import {DynamoDbTable} from "../constructs/DynamoDbTable"

export interface TablesProps {
  readonly stackName: string
}

export class DatabaseTables extends Construct {
  public readonly slackBotStateTable: DynamoDbTable
  public readonly feedbackTable: DynamoDbTable

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

    this.feedbackTable = new DynamoDbTable(this, "FeedbackTable", {
      tableName: `${props.stackName}-Feedback`,
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

  }
}
