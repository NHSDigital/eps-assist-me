import {Construct} from "constructs"
import {Duration, RemovalPolicy} from "aws-cdk-lib"
import {Queue, QueueEncryption} from "aws-cdk-lib/aws-sqs"
import {Key} from "aws-cdk-lib/aws-kms"
import {SqsEventSource} from "aws-cdk-lib/aws-lambda-event-sources"
import {LambdaFunction} from "./LambdaFunction"

export interface SimpleQueueServiceProps {
  readonly stackName: string
  readonly queueName: string
  readonly functions: Array<LambdaFunction>
}

/**
 * AWS Simple Queue Service
 * @see {@link https://aws.amazon.com/sqs/}
 */
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
      retentionPeriod: Duration.days(14), // Max
      encryption: QueueEncryption.KMS,
      encryptionMasterKey: kmsKey,
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
          maxReceiveCount: 1 // Move to DLQ after a failed attempt
        },
        deliveryDelay: Duration.minutes(0),
        visibilityTimeout: Duration.hours(1), // Really high visibility to prevent multiple calls
        enforceSSL: true
      }
    )

    // Add queues as event source for the notify function and sync knowledge base function
    const eventSource = new SqsEventSource(queue, {
      maxBatchingWindow: Duration.seconds(5),
      reportBatchItemFailures: true,
      batchSize: 100
    })

    props.functions.forEach(fn => {
      fn.function.addEventSource(eventSource)
      fn.function.addEnvironment("SQS_URL", queue.queueUrl)

      queue.grantConsumeMessages(fn.function)
    })

    // Grant the Lambda function permissions to consume messages from the queue
    this.kmsKey = kmsKey
    this.queue = queue
    this.deadLetterQueue = deadLetterQueue
  }
}
