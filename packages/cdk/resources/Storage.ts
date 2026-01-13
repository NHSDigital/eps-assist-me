import {Construct} from "constructs"
import {S3Bucket} from "../constructs/S3Bucket"
import {
  AccountRootPrincipal,
  Effect,
  IPrincipal,
  PolicyDocument,
  PolicyStatement
} from "aws-cdk-lib/aws-iam"

export interface StorageProps {
  readonly stackName: string,
  readonly deploymentRole: IPrincipal
}

export class Storage extends Construct {
  public readonly kbDocsBucket: S3Bucket

  constructor(scope: Construct, id: string, props: StorageProps) {
    super(scope, id)

    const deploymentPolicy = new PolicyStatement({
      effect: Effect.ALLOW,
      principals: [props.deploymentRole],
      actions: [
        "s3:Abort*",
        "s3:GetBucket*",
        "s3:GetObject*",
        "s3:List*",
        "s3:PutObject",
        "s3:PutObjectLegalHold",
        "s3:PutObjectRetention",
        "s3:PutObjectTagging",
        "s3:PutObjectVersionTagging"
      ],
      resources: [
        /* Will be updated when creating S3 Bucket */
      ]
    })

    const accountRootPrincipal = new AccountRootPrincipal()
    const kmsPolicy = new PolicyDocument({
      statements: [
        new PolicyStatement({
          effect: Effect.ALLOW,
          principals: [accountRootPrincipal],
          actions: ["kms:*"],
          resources: ["*"]
        }),
        new PolicyStatement({
          effect: Effect.ALLOW,
          principals: [props.deploymentRole],
          actions: [
            "kms:Encrypt",
            "kms:GenerateDataKey*"
          ],
          resources:["*"]
        })
      ]
    })

    // Create S3 bucket for knowledge base documents with encryption
    this.kbDocsBucket = new S3Bucket(this, "DocsBucket", {
      bucketName: `${props.stackName}-Docs`,
      versioned: true,
      extraBucketPolicies: [deploymentPolicy],
      extraKmsPolicies: [kmsPolicy]
    })

  }
}
