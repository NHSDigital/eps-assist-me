import {Construct} from "constructs"
import {Bucket, EventType, CfnBucket} from "aws-cdk-lib/aws-s3"
import {Function as LambdaFunction} from "aws-cdk-lib/aws-lambda"
import {Aws} from "aws-cdk-lib"
import {ServicePrincipal} from "aws-cdk-lib/aws-iam"

export interface S3LambdaNotificationProps {
  bucket: Bucket
  lambdaFunction: LambdaFunction
}

export class S3LambdaNotification extends Construct {
  constructor(scope: Construct, id: string, props: S3LambdaNotificationProps) {
    super(scope, id)

    // Add source account to Lambda permission for NCSC compliance
    props.lambdaFunction.addPermission(`S3Invoke-${this.node.id}`, {
      principal: new ServicePrincipal("s3.amazonaws.com"),
      action: "lambda:InvokeFunction",
      sourceAccount: Aws.ACCOUNT_ID,
      sourceArn: props.bucket.bucketArn
    })

    // Get the underlying CfnBucket to configure notifications directly
    const cfnBucket = props.bucket.node.defaultChild as CfnBucket

    // Configure notifications directly on the CfnBucket to avoid auto-permission creation
    cfnBucket.notificationConfiguration = {
      lambdaConfigurations: [
        {
          event: EventType.OBJECT_CREATED,
          function: props.lambdaFunction.functionArn
        },
        {
          event: EventType.OBJECT_REMOVED,
          function: props.lambdaFunction.functionArn
        },
        {
          event: EventType.OBJECT_RESTORE_COMPLETED,
          function: props.lambdaFunction.functionArn
        }
      ]
    }
  }
}
