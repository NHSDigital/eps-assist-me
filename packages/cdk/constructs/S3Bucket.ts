import {Construct} from "constructs"
import {RemovalPolicy} from "aws-cdk-lib"
import {
  Bucket,
  BucketEncryption,
  BlockPublicAccess,
  ObjectOwnership
} from "aws-cdk-lib/aws-s3"
import {Key} from "aws-cdk-lib/aws-kms"
import * as iam from "aws-cdk-lib/aws-iam"

export interface S3BucketProps {
  bucketName: string
  kmsKey?: Key
  accessLogsBucket?: Bucket
  versioned?: boolean
  bedrockExecutionRole?: iam.Role
}

export class S3Bucket extends Construct {
  public readonly bucket: Bucket
  public readonly kmsKey?: Key

  constructor(scope: Construct, id: string, props: S3BucketProps) {
    super(scope, id)

    this.bucket = new Bucket(this, props.bucketName, {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryption: props.kmsKey ? BucketEncryption.KMS : BucketEncryption.KMS,
      encryptionKey: props.kmsKey,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      enforceSSL: true,
      versioned: props.versioned ?? false,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED,
      serverAccessLogsBucket: props.accessLogsBucket,
      serverAccessLogsPrefix: props.accessLogsBucket ? "s3-access-logs/" : undefined
    })

    if (props.kmsKey && props.bedrockExecutionRole) {
      props.kmsKey.addToResourcePolicy(new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        principals: [new iam.ArnPrincipal(props.bedrockExecutionRole.roleArn)],
        actions: ["kms:Decrypt", "kms:DescribeKey"],
        resources: ["*"]
      }))
    }

    this.kmsKey = props.kmsKey
  }
}
