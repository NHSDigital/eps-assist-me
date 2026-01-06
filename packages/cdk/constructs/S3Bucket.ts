import {Construct} from "constructs"
import {RemovalPolicy} from "aws-cdk-lib"
import {
  Bucket,
  BucketEncryption,
  BlockPublicAccess,
  ObjectOwnership,
  CfnBucket,
  CfnBucketPolicy
} from "aws-cdk-lib/aws-s3"
import {Key} from "aws-cdk-lib/aws-kms"

export interface S3BucketProps {
  readonly bucketName: string
  readonly versioned: boolean
}

export class S3Bucket extends Construct {
  public readonly bucket: Bucket
  public readonly kmsKey: Key

  constructor(scope: Construct, id: string, props: S3BucketProps) {
    super(scope, id)

    const kmsKey = new Key(this, "BucketKey", {
      enableKeyRotation: true,
      description: `KMS key for ${props.bucketName} S3 bucket encryption`,
      removalPolicy: RemovalPolicy.DESTROY
    })
    kmsKey.addAlias(`alias/${props.bucketName}-s3-key`)

    const bucket = new Bucket(this, props.bucketName, {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryption: BucketEncryption.KMS,
      encryptionKey: kmsKey,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      enforceSSL: true,
      versioned: props.versioned ?? false,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED
    })

    const cfnBucket = bucket.node.defaultChild as CfnBucket
    cfnBucket.cfnOptions.metadata = {
      ...cfnBucket.cfnOptions.metadata,
      guard: {
        SuppressedRules: [
          "S3_BUCKET_REPLICATION_ENABLED",
          "S3_BUCKET_VERSIONING_ENABLED",
          "S3_BUCKET_DEFAULT_LOCK_ENABLED",
          "S3_BUCKET_LOGGING_ENABLED"
        ]
      }
    }

    const policy = bucket.policy!
    const cfnBucketPolicy = policy.node.defaultChild as CfnBucketPolicy
    cfnBucketPolicy.cfnOptions.metadata = (
      {
        ...cfnBucketPolicy.cfnOptions.metadata,
        guard: {
          SuppressedRules: [
            "S3_BUCKET_SSL_REQUESTS_ONLY"
          ]
        }
      }
    )

    this.kmsKey = kmsKey
    this.bucket = bucket
  }
}
