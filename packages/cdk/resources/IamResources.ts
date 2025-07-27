import {Construct} from "constructs"
import {
  PolicyStatement,
  Role,
  ServicePrincipal,
  ManagedPolicy
} from "aws-cdk-lib/aws-iam"
import {Bucket} from "aws-cdk-lib/aws-s3"

const EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"

export interface IamResourcesProps {
  region: string
  account: string
  kbDocsBucket: Bucket
}

export class IamResources extends Construct {
  public readonly bedrockExecutionRole: Role
  public readonly createIndexFunctionRole: Role

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

    // S3 bucket-specific access policies - requires the bucket to exist first
    // This is why Storage must be created before IamResources to avoid circular dependency
    const s3AccessListPolicy = new PolicyStatement({
      actions: ["s3:ListBucket"],
      resources: [props.kbDocsBucket.bucketArn]
    })
    s3AccessListPolicy.addCondition("StringEquals", {"aws:ResourceAccount": props.account})

    const s3AccessGetPolicy = new PolicyStatement({
      actions: ["s3:GetObject", "s3:Delete*"],
      resources: [`${props.kbDocsBucket.bucketArn}/*`]
    })
    s3AccessGetPolicy.addCondition("StringEquals", {"aws:ResourceAccount": props.account})

    // Create Bedrock execution role with all required policies for S3 and OpenSearch access
    this.bedrockExecutionRole = new Role(this, "EpsAssistMeBedrockExecutionRole", {
      assumedBy: new ServicePrincipal("bedrock.amazonaws.com"),
      description: "Role for Bedrock Knowledge Base to access S3 and OpenSearch"
    })
    this.bedrockExecutionRole.addToPolicy(bedrockExecutionRolePolicy)
    this.bedrockExecutionRole.addToPolicy(bedrockOSSPolicyForKnowledgeBase)
    this.bedrockExecutionRole.addToPolicy(bedrockKBDeleteRolePolicy)
    this.bedrockExecutionRole.addToPolicy(s3AccessListPolicy)
    this.bedrockExecutionRole.addToPolicy(s3AccessGetPolicy)

    // CreateIndex function role
    this.createIndexFunctionRole = new Role(this, "CreateIndexFunctionRole", {
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
      description: "Lambda role for creating OpenSearch index"
    })

    this.createIndexFunctionRole.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole")
    )
    this.createIndexFunctionRole.addToPolicy(new PolicyStatement({
      actions: [
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
      ],
      resources: [
        `arn:aws:aoss:${props.region}:${props.account}:collection/*`,
        `arn:aws:aoss:${props.region}:${props.account}:index/*`
      ]
    }))
  }
}
