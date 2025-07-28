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

import {bedrock} from "@cdklabs/generative-ai-cdk-constructs"
import {nagSuppressions} from "../nagSuppressions"
import {Apis} from "../resources/Apis"
import {Functions} from "../resources/Functions"
import {Storage} from "../resources/Storage"
import {Secrets} from "../resources/Secrets"
import {OpenSearchResources} from "../resources/OpenSearchResources"
import {VectorKnowledgeBaseResources} from "../resources/VectorKnowledgeBaseResources"
import {IamResources} from "../resources/IamResources"

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
    const logRetentionInDays = Number(this.node.tryGetContext("logRetentionInDays"))
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

    // Create Storage construct without Bedrock execution role to avoid circular dependency:
    // - Storage needs to exist first so IamResources can reference the S3 bucket for policies
    // - IamResources creates the Bedrock role that needs S3 access permissions
    // - KMS permissions are added manually after both constructs exist
    const storage = new Storage(this, "Storage")

    // Create IAM Resources
    const iamResources = new IamResources(this, "IamResources", {
      region,
      account,
      kbDocsBucket: storage.kbDocsBucket.bucket
    })

    // Update storage with bedrock role for KMS access
    if (storage.kbDocsBucket.kmsKey) {
      storage.kbDocsBucket.kmsKey.addToResourcePolicy(new PolicyStatement({
        effect: iam.Effect.ALLOW,
        principals: [new iam.ArnPrincipal(iamResources.bedrockExecutionRole.roleArn)],
        actions: ["kms:Decrypt", "kms:DescribeKey"],
        resources: ["*"]
      }))
    }

    // Create OpenSearch Resources
    const openSearchResources = new OpenSearchResources(this, "OpenSearchResources", {
      bedrockExecutionRole: iamResources.bedrockExecutionRole,
      createIndexFunctionRole: iamResources.createIndexFunctionRole,
      account
    })

    const endpoint = openSearchResources.collection.endpoint

    // Create VectorKnowledgeBase construct
    const vectorKB = new VectorKnowledgeBaseResources(this, "VectorKB", {
      kbName: "eps-assist-kb",
      embeddingsModel: bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_1024,
      docsBucket: storage.kbDocsBucket.bucket,
      bedrockExecutionRole: iamResources.bedrockExecutionRole
    })

    // Create Functions construct
    const functions = new Functions(this, "Functions", {
      stackName: props.stackName,
      version: props.version,
      commitId: props.commitId,
      logRetentionInDays,
      logLevel,
      createIndexFunctionRole: iamResources.createIndexFunctionRole,
      slackBotTokenParameter: secrets.slackBotTokenParameter,
      slackSigningSecretParameter: secrets.slackSigningSecretParameter,
      guardrailId: vectorKB.guardrail.guardrailId,
      guardrailVersion: vectorKB.guardrail.guardrailVersion,
      collectionId: openSearchResources.collection.collection.attrId,
      knowledgeBaseId: vectorKB.knowledgeBase.knowledgeBaseId,
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
          iamResources.bedrockExecutionRole.roleArn,
          functions.functions.createIndex.function.role?.roleArn,
          `arn:aws:iam::${account}:root`
        ]
      }])
    })
    openSearchResources.collection.collection.addDependency(aossAccessPolicy)

    // Create a custom resource to create the OpenSearch index
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
    vectorKB.knowledgeBase.node.addDependency(vectorIndex)
    vectorKB.knowledgeBase.node.addDependency(functions.functions.createIndex)
    vectorKB.knowledgeBase.node.addDependency(openSearchResources.collection.collection)
    vectorKB.knowledgeBase.node.addDependency(iamResources.bedrockExecutionRole)

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
