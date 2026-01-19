import {Construct} from "constructs"
import {Duration, RemovalPolicy} from "aws-cdk-lib"
import {Queue, QueueEncryption} from "aws-cdk-lib/aws-sqs"
import {Key} from "aws-cdk-lib/aws-kms"
import {Function} from "aws-cdk-lib/aws-lambda"
import {SqsEventSource} from "aws-cdk-lib/aws-lambda-event-sources"
export interface SimpleQueueServiceProps {
  readonly stackName: string
  readonly queueName: string
  //You can specify an integer value of 0 to 900 (15 minutes).
  readonly deliveryDelay: number
  readonly lambdaFunction: Function
}

export class SimpleQueueService extends Construct {
  public queue: Queue
  public deadLetterQueue: Queue
  public kmsKey: Key

  constructor(scope: Construct, id: string, props: SimpleQueueServiceProps) {
    super(scope, id)

    const name = `${props.stackName}-${props.queueName}`

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
      enforceSSL: true
    })

    // Create the main SQS Queue with DLQ configured
    const queue = new Queue(this, `${name}-sqs`,
      {
        queueName: `${name}-sqs`,
        encryption: QueueEncryption.KMS,
        encryptionMasterKey: kmsKey,
        deadLetterQueue: {
          queue: deadLetterQueue,
          maxReceiveCount: 3 // Move to DLQ after 3 failed attempts
        },
        deliveryDelay: Duration.seconds(props.deliveryDelay),
        enforceSSL: true
      }
    )

    // Add queue as event source for the Lambda function
    props.lambdaFunction.addEventSource(new SqsEventSource(queue, {
      batchSize: 10,
      enabled: true,
      maxBatchingWindow: Duration.seconds(60), // Wait up to 60 seconds to gather a full batch
      reportBatchItemFailures: true
    }))

    // Grant the Lambda function permissions to consume messages from the queue
    queue.grantConsumeMessages(props.lambdaFunction)

    this.kmsKey = kmsKey
    this.queue = queue
    this.deadLetterQueue = deadLetterQueue
  }
}
