import {Construct} from "constructs"
import {RemovalPolicy} from "aws-cdk-lib"
import {
  Bucket,
  BucketEncryption,
  BlockPublicAccess,
  ObjectOwnership
} from "aws-cdk-lib/aws-s3"
import {Key, Alias} from "aws-cdk-lib/aws-kms"

export interface S3BucketProps {
  readonly bucketName: string
  readonly versioned: boolean
}

export class S3Bucket extends Construct {
  public readonly bucket: Bucket
  public readonly kmsKey: Key
  public readonly kmsAlias: Alias

  constructor(scope: Construct, id: string, props: S3BucketProps) {
    super(scope, id)

    this.kmsKey = new Key(this, "BucketKey", {
      enableKeyRotation: true,
      description: `KMS key for ${props.bucketName} S3 bucket encryption`,
      removalPolicy: RemovalPolicy.DESTROY
    })

    this.kmsAlias = new Alias(this, "BucketKeyAlias", {
      aliasName: `alias/${props.bucketName}-s3-key`,
      targetKey: this.kmsKey,
      removalPolicy: RemovalPolicy.DESTROY
    })

    this.bucket = new Bucket(this, props.bucketName, {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryption: BucketEncryption.KMS,
      encryptionKey: this.kmsKey,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      enforceSSL: true,
      versioned: props.versioned ?? false,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED
    })
  }
}
