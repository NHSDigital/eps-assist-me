import {Construct} from "constructs"
import {S3Bucket} from "../constructs/S3Bucket"
import {SimpleQueueService} from "../constructs/SimpleQueueService"
import {Functions} from "./Functions"
import {Storage} from "./Storage"
import {Effect, PolicyStatement, ServicePrincipal} from "aws-cdk-lib/aws-iam"
import {EventType} from "aws-cdk-lib/aws-s3"
import {LambdaDestination, SqsDestination} from "aws-cdk-lib/aws-s3-notifications"

export interface S3LambdaNotificationProps {
  readonly stackName: string
  readonly functions: Functions
  readonly storage: Storage
}

export class S3LambdaNotification extends Construct {
  public readonly kbDocsBucket: S3Bucket

  constructor(scope: Construct, id: string, props: S3LambdaNotificationProps) {
    super(scope, id)

    const queueName = `S3-SQS`

    // Add Queue to notify S3 updates
    const queue = new SimpleQueueService(this, `${props.stackName}-${queueName}`, {
      stackName: props.stackName,
      queueName: queueName,
      batchDelay: 100,
      functions: [
        props.functions.notifyS3UploadFunction,
        props.functions.syncKnowledgeBaseFunction
      ]
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
    const processedDestination = new SqsDestination(queue.queue)
    const rawDestination = new LambdaDestination(props.functions.preprocessingFunction.function)

    // Trigger knowledge base sync only for supported document types
    const supportedExtensions = [".pdf", ".txt", ".md", ".csv", ".doc", ".docx", ".xls", ".xlsx", ".html", ".json"]

    // Add triggers for supported document types
    supportedExtensions.forEach(ext => {
      // Handle all file creation/modification events
      this.subscribeToProcessed(props, processedDestination, ext)
      this.subscribeToUploaded(props, rawDestination, ext)
    })
  }

  private subscribeToProcessed(props: S3LambdaNotificationProps, destination: SqsDestination, ext: string) {
    props.storage.kbDocsBucket.addEventNotification(
      EventType.OBJECT_CREATED,
      destination,
      {prefix: "processed/", suffix: ext}
    )

    // Handle all file deletion events
    props.storage.kbDocsBucket.addEventNotification(
      EventType.OBJECT_REMOVED,
      destination,
      {prefix: "processed/", suffix: ext}
    )
  }

  private subscribeToUploaded(props: S3LambdaNotificationProps, destination: LambdaDestination, ext: string) {
    props.storage.kbDocsBucket.addEventNotification(
      EventType.OBJECT_CREATED,
      destination,
      {prefix: "raw/", suffix: ext}
    )

    // Handle all file deletion events
    props.storage.kbDocsBucket.addEventNotification(
      EventType.OBJECT_REMOVED,
      destination,
      {prefix: "raw/", suffix: ext}
    )
  }
}
