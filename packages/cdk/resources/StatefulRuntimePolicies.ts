import {Construct} from "constructs"
import {PolicyStatement, ManagedPolicy} from "aws-cdk-lib/aws-iam"

export interface StatefulRuntimePoliciesProps {
  readonly knowledgeBaseArn: string
  readonly dataSourceArn: string
  readonly docsBucketArn: string
  readonly docsBucketKmsKeyArn: string
}

export class StatefulRuntimePolicies extends Construct {
  public readonly syncKnowledgeBasePolicy: ManagedPolicy
  public readonly preprocessingPolicy: ManagedPolicy

  constructor(scope: Construct, id: string, props: StatefulRuntimePoliciesProps) {
    super(scope, id)

    // Create managed policy for SyncKnowledgeBase Lambda function
    const syncKnowledgeBasePolicy = new PolicyStatement({
      actions: [
        "bedrock:StartIngestionJob",
        "bedrock:GetIngestionJob",
        "bedrock:ListIngestionJobs"
      ],
      resources: [
        props.knowledgeBaseArn,
        props.dataSourceArn
      ]
    })

    this.syncKnowledgeBasePolicy = new ManagedPolicy(this, "SyncKnowledgeBasePolicy", {
      description: "Policy for SyncKnowledgeBase Lambda to trigger ingestion jobs",
      statements: [syncKnowledgeBasePolicy]
    })

    //policy for the preprocessing lambda
    const preprocessingS3Policy = new PolicyStatement({
      actions: [
        "s3:GetObject",
        "s3:PutObject"
      ],
      resources: [
        `${props.docsBucketArn}/raw/*`,
        `${props.docsBucketArn}/processed/*`
      ]
    })

    const preprocessingKmsPolicy = new PolicyStatement({
      actions: [
        "kms:Decrypt",
        "kms:Encrypt",
        "kms:GenerateDataKey"
      ],
      resources: [props.docsBucketKmsKeyArn]
    })

    this.preprocessingPolicy = new ManagedPolicy(this, "PreprocessingPolicy", {
      description: "Policy for Preprocessing Lambda to read from raw/ and write to processed/",
      statements: [preprocessingS3Policy, preprocessingKmsPolicy]
    })
  }
}
