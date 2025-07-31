import {Construct} from "constructs"
import {RemovalPolicy} from "aws-cdk-lib"
import {
  Bucket,
  BucketEncryption,
  BlockPublicAccess,
  ObjectOwnership
} from "aws-cdk-lib/aws-s3"
import {Key} from "aws-cdk-lib/aws-kms"

export interface S3BucketProps {
  readonly bucketName: string
  readonly kmsKey: Key
  readonly versioned: boolean
}

export class S3Bucket extends Construct {
  public readonly bucket: Bucket
  public readonly kmsKey?: Key

  constructor(scope: Construct, id: string, props: S3BucketProps) {
    super(scope, id)

    this.bucket = new Bucket(this, props.bucketName, {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryption: BucketEncryption.KMS,
      encryptionKey: props.kmsKey,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      enforceSSL: true,
      versioned: props.versioned ?? false,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED
    })

    this.kmsKey = props.kmsKey
  }
}
