import {Construct} from "constructs"
import {S3Bucket} from "../constructs/S3Bucket"
import {SimpleQueueService} from "../constructs/SimpleQueueService"
import {Functions} from "../resources/Functions"
import {Storage} from "../resources/Storage"
import {Effect, PolicyStatement, ServicePrincipal} from "aws-cdk-lib/aws-iam"
import {EventType} from "aws-cdk-lib/aws-s3"
import {SqsDestination} from "aws-cdk-lib/aws-s3-notifications"

export interface StorageProps {
  readonly stackName: string
  readonly functions: Functions
  readonly storage: Storage
  readonly eventType: EventType
}

export class StorageNotificationQueue extends Construct {
  public readonly kbDocsBucket: S3Bucket

  constructor(scope: Construct, id: string, props: StorageProps) {
    super(scope, id)

    const eventTypeParts = props.eventType.toString().split(":")
    let eventName = props.eventType.toString()

    // Events follow format: s3:[service]:[method], so we can extract a friendly name
    // If the method is "*" (any), we just use the service name
    if (eventTypeParts.length > 1) {
      const eventTypeService = eventTypeParts[1]
      const eventTypeMethod = eventTypeParts[2] === "*" ? "" : `-${eventTypeParts[2]}`

      eventName = `${eventTypeService}${eventTypeMethod}`
    }

    const queueName = `${props.stackName}-S3-${eventName}-SQS`

    // Add Queue to notify S3 updates
    const queue = new SimpleQueueService(this, queueName, {
      stackName: props.stackName,
      queueName: queueName,
      deliveryDelay: 60, // Add a 1 minute debounce delay
      lambdaFunction: props.functions.notifyS3UploadFunction.function
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
    props.storage.kbDocsBucket.addEventNotification(
      props.eventType,
      new SqsDestination(queue.queue)
    )
  }
}
