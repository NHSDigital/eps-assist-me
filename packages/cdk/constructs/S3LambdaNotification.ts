import {Construct} from "constructs"
import {Bucket, EventType} from "aws-cdk-lib/aws-s3"
import {LambdaDestination} from "aws-cdk-lib/aws-s3-notifications"
import {Function as LambdaFunction} from "aws-cdk-lib/aws-lambda"

export interface S3LambdaNotificationProps {
  bucket: Bucket
  lambdaFunction: LambdaFunction
}

export class S3LambdaNotification extends Construct {
  constructor(scope: Construct, id: string, props: S3LambdaNotificationProps) {
    super(scope, id)

    const lambdaDestination = new LambdaDestination(props.lambdaFunction)

    // Listen for all object events to keep knowledge base in sync
    props.bucket.addEventNotification(EventType.OBJECT_CREATED, lambdaDestination)
    props.bucket.addEventNotification(EventType.OBJECT_REMOVED, lambdaDestination)
    props.bucket.addEventNotification(EventType.OBJECT_RESTORE_COMPLETED, lambdaDestination)
  }
}
