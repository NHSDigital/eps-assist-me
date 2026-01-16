import {Construct} from "constructs"
import {S3Bucket} from "../constructs/S3Bucket"
import {IPrincipal} from "aws-cdk-lib/aws-iam"
import {Key} from "aws-cdk-lib/aws-kms"
import {Bucket, IBucket} from "aws-cdk-lib/aws-s3"

export interface StorageProps {
  readonly stackName: string,
  readonly deploymentRole: IPrincipal
  readonly auditLoggingBucket: IBucket
}

export class Storage extends Construct {
  public readonly kbDocsBucket: Bucket
  public readonly kbDocsKmsKey: Key

  constructor(scope: Construct, id: string, props: StorageProps) {
    super(scope, id)

    // Create S3 bucket for knowledge base documents with encryption
    const kbDocsBucket = new S3Bucket(this, "DocsBucket", {
      bucketName: `${props.stackName}-Docs`,
      versioned: true,
      deploymentRole: props.deploymentRole,
      auditLoggingBucket: props.auditLoggingBucket
    })
    this.kbDocsBucket = kbDocsBucket.bucket
    this.kbDocsKmsKey = kbDocsBucket.kmsKey
  }
}
