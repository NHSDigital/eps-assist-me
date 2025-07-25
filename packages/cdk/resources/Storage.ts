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

export interface StorageProps {
  bedrockExecutionRole: iam.Role
}

export class Storage extends Construct {
  public readonly kbDocsBucket: Bucket
  public readonly accessLogBucket: Bucket
  public readonly kbDocsKey: Key

  constructor(scope: Construct, id: string, props: StorageProps) {
    super(scope, id)

    // Define the S3 bucket for access logs
    this.accessLogBucket = new Bucket(this, "EpsAssistAccessLogsBucket", {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryption: BucketEncryption.KMS,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      enforceSSL: true,
      versioned: false,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED
    })

    // Create a customer-managed KMS key
    this.kbDocsKey = new Key(this, "KbDocsKey", {
      enableKeyRotation: true,
      description: "KMS key for encrypting knowledge base documents"
    })

    // Use the KMS key in your S3 bucket
    this.kbDocsBucket = new Bucket(this, "EpsAssistDocsBucket", {
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      encryption: BucketEncryption.KMS,
      encryptionKey: this.kbDocsKey,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      enforceSSL: true,
      versioned: true,
      objectOwnership: ObjectOwnership.BUCKET_OWNER_ENFORCED,
      serverAccessLogsBucket: this.accessLogBucket,
      serverAccessLogsPrefix: "s3-access-logs/"
    })

    // Grant Bedrock permission to decrypt
    this.kbDocsKey.addToResourcePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.ArnPrincipal(props.bedrockExecutionRole.roleArn)],
      actions: ["kms:Decrypt", "kms:DescribeKey"],
      resources: ["*"]
    }))
  }
}
