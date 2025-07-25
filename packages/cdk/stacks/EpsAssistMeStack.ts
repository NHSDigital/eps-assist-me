import {
  App,
  Stack,
  StackProps,
  CfnOutput
} from "aws-cdk-lib"

import {PolicyStatement} from "aws-cdk-lib/aws-iam"
import * as cdk from "aws-cdk-lib"
import * as iam from "aws-cdk-lib/aws-iam"
import * as ops from "aws-cdk-lib/aws-opensearchserverless"
import * as cr from "aws-cdk-lib/custom-resources"
import {nagSuppressions} from "../nagSuppressions"
import {Apis} from "../resources/Apis"
import {Functions} from "../resources/Functions"
import {Storage} from "../resources/Storage"
import {Secrets} from "../resources/Secrets"
import {OpenSearchResources} from "../resources/OpenSearchResources"
import {BedrockResources} from "../resources/BedrockResources"

const EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
const VECTOR_INDEX_NAME = "eps-assist-os-index"

export interface EpsAssistMeStackProps extends StackProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
}

export class EpsAssistMeStack extends Stack {
  public constructor(scope: App, id: string, props: EpsAssistMeStackProps) {
    super(scope, id, props)

    // Get variables from context
    const region = Stack.of(this).region
    const account = Stack.of(this).account
    const logRetentionInDays = Number(this.node.tryGetContext("logRetentionInDays")) || 14
    const logLevel: string = this.node.tryGetContext("logLevel")

    // Get secrets from context or fail if not provided
    const slackBotToken: string = this.node.tryGetContext("slackBotToken")
    const slackSigningSecret: string = this.node.tryGetContext("slackSigningSecret")

    if (!slackBotToken || !slackSigningSecret) {
      throw new Error("Missing required context variables. Please provide slackBotToken and slackSigningSecret")
    }

    // Create Secrets construct
    const secrets = new Secrets(this, "Secrets", {
      slackBotToken,
      slackSigningSecret
    })

    // Create an IAM policy to invoke Bedrock models and access titan v1 embedding model
    const bedrockExecutionRolePolicy = new PolicyStatement()
    bedrockExecutionRolePolicy.addActions("bedrock:InvokeModel")
    bedrockExecutionRolePolicy.addResources(`arn:aws:bedrock:${region}::foundation-model/${EMBEDDING_MODEL}`)

    // Create an IAM policy to delete Bedrock knowledgebase
    const bedrockKBDeleteRolePolicy = new PolicyStatement()
    bedrockKBDeleteRolePolicy.addActions("bedrock:Delete*")
    bedrockKBDeleteRolePolicy.addResources(`arn:aws:bedrock:${region}:${account}:knowledge-base/*`)

    // Create IAM policy to call OpensearchServerless
    const bedrockOSSPolicyForKnowledgeBase = new PolicyStatement()
    bedrockOSSPolicyForKnowledgeBase.addActions("aoss:APIAccessAll")
    bedrockOSSPolicyForKnowledgeBase.addActions(
      "aoss:DeleteAccessPolicy",
      "aoss:DeleteCollection",
      "aoss:DeleteLifecyclePolicy",
      "aoss:DeleteSecurityConfig",
      "aoss:DeleteSecurityPolicy"
    )
    bedrockOSSPolicyForKnowledgeBase.addResources(`arn:aws:aoss:${region}:${account}:collection/*`)

    // Define IAM Role and add Iam policies for bedrock execution role
    const bedrockExecutionRole = new iam.Role(this, "EpsAssistMeBedrockExecutionRole", {
      assumedBy: new iam.ServicePrincipal("bedrock.amazonaws.com"),
      description: "Role for Bedrock Knowledge Base to access S3 and OpenSearch"
    })
    bedrockExecutionRole.addToPolicy(bedrockExecutionRolePolicy)
    bedrockExecutionRole.addToPolicy(bedrockOSSPolicyForKnowledgeBase)
    bedrockExecutionRole.addToPolicy(bedrockKBDeleteRolePolicy)

    // Create Storage construct
    const storage = new Storage(this, "Storage", {
      bedrockExecutionRole
    })

    // Create an IAM policy for S3 access
    const s3AccessListPolicy = new PolicyStatement({
      actions: ["s3:ListBucket"],
      resources: [storage.kbDocsBucket.bucket.bucketArn]
    })
    s3AccessListPolicy.addCondition("StringEquals", {"aws:ResourceAccount": account})

    // Create an IAM policy for S3 access
    const s3AccessGetPolicy = new PolicyStatement({
      actions: ["s3:GetObject", "s3:Delete*"],
      resources: [`${storage.kbDocsBucket.bucket.bucketArn}/*`]
    })
    s3AccessGetPolicy.addCondition("StringEquals", {"aws:ResourceAccount": account})

    bedrockExecutionRole.addToPolicy(s3AccessListPolicy)
    bedrockExecutionRole.addToPolicy(s3AccessGetPolicy)

    // Define createIndexFunction execution role and policy. Managed role 'AWSLambdaBasicExecutionRole'
    const createIndexFunctionRole = new iam.Role(this, "CreateIndexFunctionRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      description: "Lambda role for creating OpenSearch index"
    })

    createIndexFunctionRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole")
    )
    createIndexFunctionRole.addToPolicy(new PolicyStatement({
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
        `arn:aws:aoss:${region}:${account}:collection/*`,
        `arn:aws:aoss:${region}:${account}:index/*`
      ],
      effect: iam.Effect.ALLOW
    }))

    // Create OpenSearch Resources
    const openSearchResources = new OpenSearchResources(this, "OpenSearchResources", {
      bedrockExecutionRole,
      createIndexFunctionRole,
      account
    })

    const endpoint = openSearchResources.collection.endpoint

    // Create Bedrock Resources
    const bedrockResources = new BedrockResources(this, "BedrockResources", {
      bedrockExecutionRole,
      osCollection: openSearchResources.collection.collection,
      kbDocsBucket: storage.kbDocsBucket.bucket,
      region
    })

    // Create Functions construct
    const functions = new Functions(this, "Functions", {
      stackName: props.stackName,
      version: props.version,
      commitId: props.commitId,
      logRetentionInDays,
      logLevel,
      createIndexFunctionRole,
      slackBotTokenParameter: secrets.slackBotTokenParameter,
      slackSigningSecretParameter: secrets.slackSigningSecretParameter,
      guardrailId: bedrockResources.guardrail.guardrailId,
      guardrailVersion: bedrockResources.guardrail.guardrailVersionId,
      collectionId: openSearchResources.collection.collection.attrId,
      knowledgeBaseId: bedrockResources.knowledgeBase.attrKnowledgeBaseId,
      region,
      account,
      slackBotTokenSecret: secrets.slackBotTokenSecret,
      slackBotSigningSecret: secrets.slackBotSigningSecret
    })

    // Define OpenSearchServerless access policy to access the index and collection
    // from the Amazon Bedrock execution role and the lambda execution role
    const aossAccessPolicy = new ops.CfnAccessPolicy(this, "aossAccessPolicy", {
      name: "eps-assist-access-policy",
      type: "data",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: ["collection/*"], Permission: ["aoss:*"]},
          {ResourceType: "index", Resource: ["index/*/*"], Permission: ["aoss:*"]}
        ],
        // Add principal of bedrock execution role and lambda execution role
        Principal: [
          bedrockExecutionRole.roleArn,
          functions.functions.createIndex.function.role?.roleArn,
          `arn:aws:iam::${account}:root`
        ]
      }])
    })
    openSearchResources.collection.collection.addDependency(aossAccessPolicy)

    const vectorIndex = new cr.AwsCustomResource(this, "VectorIndex", {
      installLatestAwsSdk: true,
      onCreate: {
        service: "Lambda",
        action: "invoke",
        parameters: {
          FunctionName: functions.functions.createIndex.function.functionName,
          InvocationType: "RequestResponse",
          Payload: JSON.stringify({
            RequestType: "Create",
            CollectionName: openSearchResources.collection.collection.name,
            IndexName: VECTOR_INDEX_NAME,
            Endpoint: endpoint
          })
        },
        physicalResourceId: cr.PhysicalResourceId.of("VectorIndex-eps-assist-os-index")
      },
      onDelete: {
        service: "Lambda",
        action: "invoke",
        parameters: {
          FunctionName: functions.functions.createIndex.function.functionName,
          InvocationType: "RequestResponse",
          Payload: JSON.stringify({
            RequestType: "Delete",
            CollectionName: openSearchResources.collection.collection.name,
            IndexName: VECTOR_INDEX_NAME,
            Endpoint: endpoint
          })
        }
      },
      policy: cr.AwsCustomResourcePolicy.fromStatements([
        new iam.PolicyStatement({
          actions: ["lambda:InvokeFunction"],
          resources: [functions.functions.createIndex.function.functionArn]
        })
      ]),
      timeout: cdk.Duration.seconds(60)
    })

    // Ensure vectorIndex depends on collection
    vectorIndex.node.addDependency(openSearchResources.collection.collection)

    // add a dependency for bedrock kb on the custom resource. Enables vector index to be created before KB
    bedrockResources.knowledgeBase.node.addDependency(vectorIndex)
    bedrockResources.knowledgeBase.node.addDependency(functions.functions.createIndex)
    bedrockResources.knowledgeBase.node.addDependency(openSearchResources.collection.collection)
    bedrockResources.knowledgeBase.node.addDependency(bedrockExecutionRole)

    // Create Apis and pass the Lambda function
    const apis = new Apis(this, "Apis", {
      stackName: props.stackName,
      logRetentionInDays,
      enableMutalTls: false,
      functions: {
        slackBot: functions.functions.slackBot
      }
    })

    // Output: SlackBot Endpoint
    new CfnOutput(this, "SlackBotEndpoint", {
      value: `https://${apis.apis["api"].api.domainName?.domainName}/slack/ask-eps`
    })

    // Final CDK Nag Suppressions
    nagSuppressions(this)
  }
}
