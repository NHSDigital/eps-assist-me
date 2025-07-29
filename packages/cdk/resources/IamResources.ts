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

export interface IamResourcesProps {
  region: string
  account: string
  kbDocsBucket: Bucket
}

export class IamResources extends Construct {
  public readonly bedrockExecutionRole: Role
  public readonly createIndexManagedPolicy: ManagedPolicy

  constructor(scope: Construct, id: string, props: IamResourcesProps) {
    super(scope, id)

    // Create Bedrock execution role policies for embedding model access
    const bedrockExecutionRolePolicy = new PolicyStatement()
    bedrockExecutionRolePolicy.addActions("bedrock:InvokeModel")
    bedrockExecutionRolePolicy.addResources(`arn:aws:bedrock:${props.region}::foundation-model/${EMBEDDING_MODEL}`)

    // Policy for Bedrock Knowledge Base deletion operations
    const bedrockKBDeleteRolePolicy = new PolicyStatement()
    bedrockKBDeleteRolePolicy.addActions("bedrock:Delete*")
    bedrockKBDeleteRolePolicy.addResources(`arn:aws:bedrock:${props.region}:${props.account}:knowledge-base/*`)

    // OpenSearch Serverless access policy for Knowledge Base operations
    const bedrockOSSPolicyForKnowledgeBase = new PolicyStatement()
    bedrockOSSPolicyForKnowledgeBase.addActions("aoss:APIAccessAll")
    bedrockOSSPolicyForKnowledgeBase.addActions(
      "aoss:DeleteAccessPolicy",
      "aoss:DeleteCollection",
      "aoss:DeleteLifecyclePolicy",
      "aoss:DeleteSecurityConfig",
      "aoss:DeleteSecurityPolicy"
    )
    bedrockOSSPolicyForKnowledgeBase.addResources(`arn:aws:aoss:${props.region}:${props.account}:collection/*`)

    // S3 bucket-specific access policies
    const s3AccessListPolicy = new PolicyStatement()
    s3AccessListPolicy.addActions("s3:ListBucket")
    s3AccessListPolicy.addResources(props.kbDocsBucket.bucketArn)
    s3AccessListPolicy.addCondition("StringEquals", {"aws:ResourceAccount": props.account})

    const s3AccessGetPolicy = new PolicyStatement()
    s3AccessGetPolicy.addActions("s3:GetObject")
    s3AccessGetPolicy.addResources(`${props.kbDocsBucket.bucketArn}/*`)
    s3AccessGetPolicy.addCondition("StringEquals", {"aws:ResourceAccount": props.account})

    // Create managed policy for Bedrock execution role
    const bedrockExecutionManagedPolicy = new ManagedPolicy(this, "BedrockExecutionManagedPolicy", {
      description: "Policy for Bedrock Knowledge Base to access S3 and OpenSearch"
    })
    bedrockExecutionManagedPolicy.addStatements(bedrockExecutionRolePolicy)
    bedrockExecutionManagedPolicy.addStatements(bedrockKBDeleteRolePolicy)
    bedrockExecutionManagedPolicy.addStatements(bedrockOSSPolicyForKnowledgeBase)
    bedrockExecutionManagedPolicy.addStatements(s3AccessListPolicy)
    bedrockExecutionManagedPolicy.addStatements(s3AccessGetPolicy)

    // Create Bedrock execution role with managed policy
    this.bedrockExecutionRole = new Role(this, "EpsAssistMeBedrockExecutionRole", {
      assumedBy: new ServicePrincipal("bedrock.amazonaws.com"),
      description: "Role for Bedrock Knowledge Base to access S3 and OpenSearch",
      managedPolicies: [bedrockExecutionManagedPolicy]
    })

    // Create managed policy for CreateIndex Lambda function
    const createIndexPolicy = new PolicyStatement()
    createIndexPolicy.addActions(
      "aoss:APIAccessAll",
      "aoss:DescribeIndex",
      "aoss:ReadDocument",
      "aoss:CreateIndex",
      "aoss:DeleteIndex",
      "aoss:UpdateIndex",
      "aoss:WriteDocument",
      "aoss:CreateCollectionItems",
      "aoss:DeleteCollectionItems",
      "aoss:UpdateCollectionItems",
      "aoss:DescribeCollectionItems"
    )
    createIndexPolicy.addResources(
      `arn:aws:aoss:${props.region}:${props.account}:collection/*`,
      `arn:aws:aoss:${props.region}:${props.account}:index/*`
    )

    this.createIndexManagedPolicy = new ManagedPolicy(this, "CreateIndexManagedPolicy", {
      description: "Policy for Lambda to create OpenSearch index"
    })
    this.createIndexManagedPolicy.addStatements(createIndexPolicy)
  }
}
