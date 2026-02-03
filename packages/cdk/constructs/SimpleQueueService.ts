import {Construct} from "constructs"
import {Duration, RemovalPolicy} from "aws-cdk-lib"
import {Queue, QueueEncryption} from "aws-cdk-lib/aws-sqs"
import {Key} from "aws-cdk-lib/aws-kms"
import {SqsEventSource} from "aws-cdk-lib/aws-lambda-event-sources"
import {Functions} from "../resources/Functions"

export interface SimpleQueueServiceProps {
  readonly stackName: string
  readonly queueName: string
  readonly batchDelay: number
  readonly functions: Functions
}

export class SimpleQueueService extends Construct {
  public queue: Queue
  public deadLetterQueue: Queue
  public kmsKey: Key

  constructor(scope: Construct, id: string, props: SimpleQueueServiceProps) {
    super(scope, id)

    const name = `${props.stackName}-${props.queueName}`.toLocaleLowerCase()

    const kmsKey = new Key(this, `${name}-queue-key`, {
      enableKeyRotation: true,
      description: `KMS key for ${props.queueName} queue and dead-letter queue encryption`,
      removalPolicy: RemovalPolicy.DESTROY
    })

    // Create a Dead-Letter Queue (DLQ) for handling failed messages, to help with debugging
    const deadLetterQueue = new Queue(this, `${name}-dlq`, {
      queueName: `${name}-dlq`,
      retentionPeriod: Duration.days(14), // Max 14
      encryption: QueueEncryption.KMS,
      encryptionMasterKey: kmsKey,
      visibilityTimeout: Duration.seconds(60),
      enforceSSL: true
    })

    // Create the main SQS Queue with DLQ configured
    const queue = new Queue(this, name,
      {
        queueName: name,
        encryption: QueueEncryption.KMS,
        encryptionMasterKey: kmsKey,
        deadLetterQueue: {
          queue: deadLetterQueue,
          maxReceiveCount: 3 // Move to DLQ after 3 failed attempts
        },
        deliveryDelay: Duration.seconds(10),
        visibilityTimeout: Duration.seconds(60),
        enforceSSL: true
      }
    )

    // Add queues as event source for the notify function and sync knowledge base function
    const eventSource = new SqsEventSource(queue, {
      maxBatchingWindow: Duration.seconds(props.batchDelay),
      reportBatchItemFailures: true
    })

    props.functions.notifyS3UploadFunction.function.addEventSource(eventSource)
    props.functions.syncKnowledgeBaseFunction.function.addEventSource(eventSource)
    props.functions.preprocessingFunction.function.addEventSource(eventSource)

    // Grant the Lambda function permissions to consume messages from the queue
    queue.grantConsumeMessages(props.functions.notifyS3UploadFunction.function)
    queue.grantConsumeMessages(props.functions.syncKnowledgeBaseFunction.function)
    queue.grantConsumeMessages(props.functions.preprocessingFunction.function)

    this.kmsKey = kmsKey
    this.queue = queue
    this.deadLetterQueue = deadLetterQueue
  }
}
