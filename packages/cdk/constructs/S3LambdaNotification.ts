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

    // Use CDK's built-in S3 notification
    props.bucket.addEventNotification(
      EventType.OBJECT_CREATED,
      new LambdaDestination(props.lambdaFunction)
    )
  }
}
