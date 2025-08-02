import {Construct} from "constructs"
import {Key} from "aws-cdk-lib/aws-kms"
import {S3Bucket} from "../constructs/S3Bucket"

export interface StorageProps {
  readonly stackName: string
}

export class Storage extends Construct {
  public readonly kbDocsBucket: S3Bucket
  public readonly kbDocsKey: Key

  constructor(scope: Construct, id: string, props: StorageProps) {
    super(scope, id)

    // Create customer-managed KMS key for knowledge base document encryption
    this.kbDocsKey = new Key(this, "KbDocsKey", {
      enableKeyRotation: true,
      description: "KMS key for encrypting knowledge base documents"
    })

    // Create S3 bucket for knowledge base documents with encryption
    this.kbDocsBucket = new S3Bucket(this, "DocsBucket", {
      bucketName: `${props.stackName}-Docs`,
      kmsKey: this.kbDocsKey,
      versioned: true
    })
  }
}
