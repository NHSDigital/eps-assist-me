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
    const defaultVisibilityTimeout = 60

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

    // Get the longest timeout of the functions to prevent queue events due to visibility timeouts
    const allTimeouts = props.functions.map(item => item.function.timeout?.toSeconds() ?? 0)
    const maxTimeout = Math.max(defaultVisibilityTimeout, ...allTimeouts)

    // Create the main SQS Queue with DLQ configured
    const queue = new Queue(this, name,
      {
        queueName: name,
        encryption: QueueEncryption.KMS,
        encryptionMasterKey: kmsKey,
        deadLetterQueue: {
          queue: deadLetterQueue,
          maxReceiveCount: 5
        },
        visibilityTimeout: Duration.seconds(maxTimeout),
        enforceSSL: true
      }
    )

    // Add queues as event source for the notify function and sync knowledge base function
    const eventSource = new SqsEventSource(queue, {
      maxBatchingWindow: Duration.seconds(maxTimeout),
      batchSize: 50,
      reportBatchItemFailures: true
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
