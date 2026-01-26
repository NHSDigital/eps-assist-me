import {Construct} from "constructs"
import {Bucket, EventType} from "aws-cdk-lib/aws-s3"
import {LambdaDestination} from "aws-cdk-lib/aws-s3-notifications"
import {Function as LambdaFunction} from "aws-cdk-lib/aws-lambda"

export interface S3LambdaNotificationProps {
  bucket: Bucket
  lambdaFunction: LambdaFunction
  prefix?: string
}

export class S3LambdaNotification extends Construct {
  constructor(scope: Construct, id: string, props: S3LambdaNotificationProps) {
    super(scope, id)

    const lambdaDestination = new LambdaDestination(props.lambdaFunction)

    // Trigger knowledge base sync only for supported document types
    const supportedExtensions = [".pdf", ".txt", ".md", ".csv", ".doc", ".docx", ".xls", ".xlsx", ".html", ".json"]

    supportedExtensions.forEach(ext => {
      const filter: {suffix: string; prefix?: string} = {suffix: ext}
      if (props.prefix) {
        filter.prefix = props.prefix
      }

      // Handle all file creation/modification events
      props.bucket.addEventNotification(
        EventType.OBJECT_CREATED,
        lambdaDestination,
        filter
      )

      // Handle all file deletion events
      props.bucket.addEventNotification(
        EventType.OBJECT_REMOVED,
        lambdaDestination,
        filter
      )
    })
  }
}
