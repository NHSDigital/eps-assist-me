import {Construct} from "constructs"
import {
  PolicyStatement,
  Role,
  ServicePrincipal,
  ManagedPolicy
} from "aws-cdk-lib/aws-iam"
import {Bucket} from "aws-cdk-lib/aws-s3"

// Amazon Titan embedding model for vector generation
const EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"

export interface BedrockExecutionRoleProps {
  readonly region: string
  readonly account: string
  readonly kbDocsBucket: Bucket
}

export class BedrockExecutionRole extends Construct {
  public readonly role: Role

  constructor(scope: Construct, id: string, props: BedrockExecutionRoleProps) {
    super(scope, id)

    // Create Bedrock execution role policies for embedding model access
    const bedrockExecutionRolePolicy = new PolicyStatement({
      actions: ["bedrock:InvokeModel"],
      resources: [`arn:aws:bedrock:${props.region}::foundation-model/${EMBEDDING_MODEL}`]
    })

    // Policy for Bedrock Knowledge Base deletion operations
    const bedrockKBDeleteRolePolicy = new PolicyStatement({
      actions: ["bedrock:Delete*"],
      resources: [`arn:aws:bedrock:${props.region}:${props.account}:knowledge-base/*`]
    })

    // OpenSearch Serverless access policy for Knowledge Base operations
    const bedrockOSSPolicyForKnowledgeBase = new PolicyStatement({
      actions: [
        "aoss:APIAccessAll",
        "aoss:DeleteAccessPolicy",
        "aoss:DeleteCollection",
        "aoss:DeleteLifecyclePolicy",
        "aoss:DeleteSecurityConfig",
        "aoss:DeleteSecurityPolicy"
      ],
      resources: [`arn:aws:aoss:${props.region}:${props.account}:collection/*`]
    })

    // S3 bucket-specific access policies
    const s3AccessListPolicy = new PolicyStatement({
      actions: ["s3:ListBucket"],
      resources: [props.kbDocsBucket.bucketArn],
      conditions: {"StringEquals": {"aws:ResourceAccount": props.account}}
    })

    const s3AccessGetPolicy = new PolicyStatement({
      actions: ["s3:GetObject"],
      resources: [`${props.kbDocsBucket.bucketArn}/*`],
      conditions: {"StringEquals": {"aws:ResourceAccount": props.account}}
    })

    // KMS permissions for S3 bucket encryption
    const kmsAccessPolicy = new PolicyStatement({
      actions: ["kms:Decrypt", "kms:DescribeKey"],
      resources: ["*"],
      conditions: {"StringEquals": {"aws:ResourceAccount": props.account}}
    })

    // Create managed policy for Bedrock execution role
    const bedrockExecutionManagedPolicy = new ManagedPolicy(this, "Policy", {
      description: "Policy for Bedrock Knowledge Base to access S3 and OpenSearch",
      statements: [
        bedrockExecutionRolePolicy,
        bedrockKBDeleteRolePolicy,
        bedrockOSSPolicyForKnowledgeBase,
        s3AccessListPolicy,
        s3AccessGetPolicy,
        kmsAccessPolicy
      ]
    })

    // Create Bedrock execution role with managed policy
    this.role = new Role(this, "Role", {
      assumedBy: new ServicePrincipal("bedrock.amazonaws.com"),
      description: "Role for Bedrock Knowledge Base to access S3 and OpenSearch",
      managedPolicies: [bedrockExecutionManagedPolicy]
    })
  }
}
