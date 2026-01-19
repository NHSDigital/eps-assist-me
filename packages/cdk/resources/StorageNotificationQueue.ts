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
}

export class StorageNotificationQueue extends Construct {
  public readonly kbDocsBucket: S3Bucket

  constructor(scope: Construct, id: string, props: StorageProps) {
    super(scope, id)

    // Add Queue to notify S3 updates
    const queue = new SimpleQueueService(this, "S3UpdateQueue", {
      stackName: props.stackName,
      queueName: "S3UpdateQueue",
      deliveryDelay: 60, // Add a 1 minute debounce delay
      lambdaFunction: props.functions.notifyS3UploadFunction.function
    })

    // Subscribe to S3 bucket events to send notifications to the SQS queue
    queue.kmsKey.addAlias(`alias/${queue.queue.queueName}-s3-key`)
    queue.kmsKey.addToResourcePolicy(new PolicyStatement({
      effect: Effect.ALLOW,
      principals: [new ServicePrincipal("s3.amazonaws.com")],
      actions: ["kms:GenerateDataKey", "kms:Decrypt"],
      resources: ["*"],
      conditions: {
        ArnLike: {
          "aws:SourceArn": props.storage.kbDocsBucket.bucket.bucketArn
        }
      }
    }))

    // Add trigger for SQS queue to Lambda function
    props.storage.kbDocsBucket.bucket.addEventNotification(
      EventType.OBJECT_CREATED,
      new SqsDestination(queue.queue)
    )
  }
}
