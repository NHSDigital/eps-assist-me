import {Construct} from "constructs"
import {S3Bucket} from "../constructs/S3Bucket"
import {IPrincipal} from "aws-cdk-lib/aws-iam"

export interface StorageProps {
  readonly stackName: string,
  readonly deploymentRole: IPrincipal
}

export class Storage extends Construct {
  public readonly kbDocsBucket: S3Bucket

  constructor(scope: Construct, id: string, props: StorageProps) {
    super(scope, id)

    // Create S3 bucket for knowledge base documents with encryption
    this.kbDocsBucket = new S3Bucket(this, "DocsBucket", {
      bucketName: `${props.stackName}-Docs`,
      versioned: true,
      deploymentRole: props.deploymentRole
    })

  }
}
