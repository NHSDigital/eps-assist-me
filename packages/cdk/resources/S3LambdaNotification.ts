import {Construct} from "constructs"
import {S3Bucket} from "../constructs/S3Bucket"
import {SimpleQueueService} from "../constructs/SimpleQueueService"
import {Functions} from "./Functions"
import {Storage} from "./Storage"
import {Effect, PolicyStatement, ServicePrincipal} from "aws-cdk-lib/aws-iam"
import {EventType} from "aws-cdk-lib/aws-s3"
import {SqsDestination} from "aws-cdk-lib/aws-s3-notifications"

export interface StorageProps {
  readonly stackName: string
  readonly functions: Functions
  readonly storage: Storage
}

export class StorageNotificationQueue extends Construct {
  public readonly kbDocsBucket: S3Bucket

  constructor(scope: Construct, id: string, props: StorageProps) {
    super(scope, id)

    const queueName = `${props.stackName}-S3-SQS`

    // Add Queue to notify S3 updates
    const queue = new SimpleQueueService(this, queueName, {
      stackName: props.stackName,
      queueName: queueName,
      deliveryDelay: 60, // Add a 1 minute debounce delay
      fuctions: props.functions
    })

    // Subscribe to S3 bucket events to send notifications to the SQS queue
    queue.kmsKey.addAlias(`alias/${queueName}-key`)
    queue.kmsKey.addToResourcePolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      principals: [new ServicePrincipal("s3.amazonaws.com")],
      actions: ["kms:GenerateDataKey", "kms:Decrypt"],
      resources: ["*"],
      conditions: {
        ArnLike: {
          "aws:SourceArn": props.storage.kbDocsBucket.bucketArn
        }
      }
    }))

    // Add trigger for SQS queue to Lambda function
    const destination = new SqsDestination(queue.queue)

    // Trigger knowledge base sync only for supported document types
    const supportedExtensions = [".pdf", ".txt", ".md", ".csv", ".doc", ".docx", ".xls", ".xlsx", ".html", ".json"]

    supportedExtensions.forEach(ext => {
      // Handle all file creation/modification events
      props.storage.kbDocsBucket.addEventNotification(
        EventType.OBJECT_CREATED,
        destination,
        {suffix: ext}
      )

      // Handle all file deletion events
      props.storage.kbDocsBucket.addEventNotification(
        EventType.OBJECT_REMOVED,
        destination,
        {suffix: ext}
      )
    })
  }
}
