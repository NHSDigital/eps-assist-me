import {Construct} from "constructs"
import {Duration} from "aws-cdk-lib"
import {PolicyStatement} from "aws-cdk-lib/aws-iam"
import {Bucket} from "aws-cdk-lib/aws-s3"
import {Function as LambdaFunction} from "aws-cdk-lib/aws-lambda"
import {AwsCustomResource, AwsCustomResourcePolicy, PhysicalResourceId} from "aws-cdk-lib/custom-resources"

export interface S3LambdaNotificationProps {
  bucket: Bucket
  lambdaFunction: LambdaFunction
  events?: Array<string>
}

export class S3LambdaNotification extends Construct {
  constructor(scope: Construct, id: string, props: S3LambdaNotificationProps) {
    super(scope, id)

    const events = props.events ?? ["s3:ObjectCreated:*"]

    // Create S3 bucket notification using custom resource
    new AwsCustomResource(this, "BucketNotification", {
      onCreate: {
        service: "S3",
        action: "putBucketNotificationConfiguration",
        parameters: {
          Bucket: props.bucket.bucketName,
          NotificationConfiguration: {
            LambdaConfigurations: [{
              Id: "LambdaNotification",
              LambdaFunctionArn: props.lambdaFunction.functionArn,
              Events: events
            }]
          }
        },
        physicalResourceId: PhysicalResourceId.of(`${props.bucket.bucketName}-notification`)
      },
      onDelete: {
        service: "S3",
        action: "putBucketNotificationConfiguration",
        parameters: {
          Bucket: props.bucket.bucketName,
          NotificationConfiguration: {}
        }
      },
      policy: AwsCustomResourcePolicy.fromStatements([
        new PolicyStatement({
          actions: ["s3:PutBucketNotification", "s3:GetBucketNotification"],
          resources: [props.bucket.bucketArn]
        }),
        new PolicyStatement({
          actions: ["lambda:AddPermission", "lambda:RemovePermission"],
          resources: [props.lambdaFunction.functionArn]
        })
      ]),
      timeout: Duration.minutes(5)
    })

    // Add Lambda permission for S3 to invoke the function
    new AwsCustomResource(this, "LambdaPermission", {
      onCreate: {
        service: "Lambda",
        action: "addPermission",
        parameters: {
          FunctionName: props.lambdaFunction.functionName,
          StatementId: "S3InvokePermission",
          Action: "lambda:InvokeFunction",
          Principal: "s3.amazonaws.com",
          SourceArn: props.bucket.bucketArn
        },
        physicalResourceId: PhysicalResourceId.of(`${props.lambdaFunction.functionName}-s3-permission`)
      },
      onDelete: {
        service: "Lambda",
        action: "removePermission",
        parameters: {
          FunctionName: props.lambdaFunction.functionName,
          StatementId: "S3InvokePermission"
        }
      },
      policy: AwsCustomResourcePolicy.fromStatements([
        new PolicyStatement({
          actions: ["lambda:AddPermission", "lambda:RemovePermission"],
          resources: [props.lambdaFunction.functionArn]
        })
      ])
    })
  }
}
