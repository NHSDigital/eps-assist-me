import {Construct} from "constructs"
import {Key} from "aws-cdk-lib/aws-kms"
import {S3Bucket} from "../constructs/S3Bucket"
import {DynamoDbTable} from "../constructs/DynamoDbTable"

export interface StorageProps {
  readonly stackName: string
}

export class Storage extends Construct {
  public readonly kbDocsBucket: S3Bucket
  public readonly kbDocsKey: Key
  public readonly conversationTable: DynamoDbTable
  public readonly conversationKey: Key

  constructor(scope: Construct, id: string, props: StorageProps) {
    super(scope, id)

    // Create customer-managed KMS key for knowledge base document encryption
    this.kbDocsKey = new Key(this, "KbDocsKey", {
      enableKeyRotation: true,
      description: "KMS key for encrypting knowledge base documents"
    })

    // Create S3 bucket for knowledge base documents with encryption
    this.kbDocsBucket = new S3Bucket(this, "DocsBucket", {
      bucketName: `${props.stackName}-Docs`,
      kmsKey: this.kbDocsKey,
      versioned: true
    })

    // create KMS key for conversation table encryption
    this.conversationKey = new Key(this, "ConversationKey", {
      enableKeyRotation: true,
      description: "KMS key for encrypting conversation sessions"
    })

    // create DynamoDB table for conversation sessions
    this.conversationTable = new DynamoDbTable(this, "ConversationTable", {
      tableName: `${props.stackName}-conversations`,
      kmsKey: this.conversationKey
    })
  }
}
