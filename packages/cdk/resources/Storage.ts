import {Construct} from "constructs"
import {Key} from "aws-cdk-lib/aws-kms"
import {S3Bucket} from "../constructs/S3Bucket"

export class Storage extends Construct {
  public readonly kbDocsBucket: S3Bucket
  public readonly accessLogBucket: S3Bucket
  public readonly kbDocsKey: Key

  constructor(scope: Construct, id: string) {
    super(scope, id)

    // Define the S3 bucket for access logs
    this.accessLogBucket = new S3Bucket(this, "AccessLogsBucket", {
      bucketName: "EpsAssistAccessLogsBucket",
      versioned: false
    })

    // Create a customer-managed KMS key
    this.kbDocsKey = new Key(this, "KbDocsKey", {
      enableKeyRotation: true,
      description: "KMS key for encrypting knowledge base documents"
    })

    // Use the KMS key in your S3 bucket
    this.kbDocsBucket = new S3Bucket(this, "DocsBucket", {
      bucketName: "EpsAssistDocsBucket",
      kmsKey: this.kbDocsKey,
      accessLogsBucket: this.accessLogBucket.bucket,
      versioned: true
    })
  }
}
