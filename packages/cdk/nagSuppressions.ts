/* eslint-disable max-len, @typescript-eslint/no-unused-vars */
import {Stack} from "aws-cdk-lib"
import {NagPackSuppression, NagSuppressions} from "cdk-nag"

export const nagSuppressions = (stack: Stack) => {
  const stackName = stack.node.tryGetContext("stackName") || "epsam"
  const account = Stack.of(stack).account
  // Suppress granular wildcard on log stream for SlackBot Lambda
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/Functions/SlackBotLambda/LambdaPutLogsManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Wildcard permissions for log stream access are required and scoped appropriately.",
        appliesTo: [
          "Resource::<FunctionsSlackBotLambdaLambdaLogGroup3597D783.Arn>:log-stream:*"
        ]
      }
    ]
  )

  // Suppress wildcard log permissions for CreateIndex Lambda
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/Functions/CreateIndexFunction/LambdaPutLogsManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Wildcard permissions are required for log stream access under known paths.",
        appliesTo: [
          "Resource::<FunctionsCreateIndexFunctionLambdaLogGroupB45008DF.Arn>:log-stream:*"
        ]
      }
    ]
  )

  // Suppress wildcard log permissions for SyncKnowledgeBase Lambda
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/Functions/SyncKnowledgeBaseFunction/LambdaPutLogsManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Wildcard permissions are required for log stream access under known paths.",
        appliesTo: [
          "Resource::<FunctionsSyncKnowledgeBaseFunctionLambdaLogGroupB19BE2BE.Arn>:log-stream:*"
        ]
      }
    ]
  )

  // Suppress API Gateway validation warning for Apis construct
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/Apis/EpsAssistApiGateway/ApiGateway/Resource",
    [
      {
        id: "AwsSolutions-APIG2",
        reason: "Validation is handled within Lambda; request validation is intentionally omitted."
      }
    ]
  )

  // Suppress AWS managed policy usage in default CDK role
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/AWS679f53fac002430cb0da5b7982bd2287/ServiceRole/Resource",
    [
      {
        id: "AwsSolutions-IAM4",
        reason: "Auto-generated service role uses AWS managed policy, which is acceptable here."
      }
    ]
  )

  // Suppress unauthenticated API route warnings
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/Apis/EpsAssistApiGateway/ApiGateway/Default/slack/events/POST/Resource",
    [
      {
        id: "AwsSolutions-APIG4",
        reason: "Slack command endpoint is intentionally unauthenticated."
      },
      {
        id: "AwsSolutions-COG4",
        reason: "Cognito not required for this public endpoint."
      }
    ]
  )

  // Suppress missing WAF on API stage for Apis construct
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/Apis/EpsAssistApiGateway/ApiGateway/DeploymentStage.prod/Resource",
    [
      {
        id: "AwsSolutions-APIG3",
        reason: "WAF not in current scope; may be added later."
      }
    ]
  )

  // Suppress IAM wildcard permissions for Bedrock execution role policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/BedrockExecutionRole/Policy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Bedrock Knowledge Base requires these permissions to access S3 documents and OpenSearch collection.",
        appliesTo: [
          "Resource::<StorageDocsBucketepsamDocsF25F63F1.Arn>/*",
          "Resource::<StorageDocsBucketepsampr27Docs28B71689.Arn>/*",
          "Action::bedrock:Delete*",
          `Resource::arn:aws:bedrock:eu-west-2:${account}:knowledge-base/*`,
          `Resource::arn:aws:aoss:eu-west-2:${account}:collection/*`,
          "Resource::*"
        ]
      }
    ]
  )

  // Suppress wildcard permissions for CreateIndex policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/RuntimePolicies/CreateIndexPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Lambda needs access to all OpenSearch collections and indexes to create and manage indexes.",
        appliesTo: [
          `Resource::arn:aws:aoss:eu-west-2:${account}:collection/*`,
          `Resource::arn:aws:aoss:eu-west-2:${account}:index/*`
        ]
      }
    ]
  )

  // Suppress wildcard permissions for SlackBot policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/RuntimePolicies/SlackBotPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "SlackBot Lambda needs wildcard access for Lambda functions (self-invocation), KMS operations, and Bedrock prompts.",
        appliesTo: [
          `Resource::arn:aws:lambda:eu-west-2:${account}:function:*`,
          `Resource::arn:aws:bedrock:eu-west-2:${account}:prompt/*`,
          `Resource::arn:aws:bedrock:eu-west-2:${account}:prompt/${stackName}-queryReformulation:*`,
          "Action::kms:GenerateDataKey*",
          "Action::kms:ReEncrypt*"
        ]
      }
    ]
  )

  // Suppress S3 server access logs for knowledge base documents bucket
  safeAddNagSuppression(
    stack,
    `/EpsAssistMeStack/Storage/DocsBucket/${stackName}-Docs/Resource`,
    [
      {
        id: "AwsSolutions-S1",
        reason: "Server access logging not required for knowledge base documents bucket."
      }
    ]
  )

  // Suppress secrets without rotation
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/Secrets/SlackBotToken/Secret/Resource",
    [
      {
        id: "AwsSolutions-SMG4",
        reason: "Slack bot token rotation is handled manually as part of the Slack app configuration process."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/Secrets/SlackBotSigning/Secret/Resource",
    [
      {
        id: "AwsSolutions-SMG4",
        reason: "Slack signing secret rotation is handled manually as part of the Slack app configuration process."
      }
    ]
  )

  // Suppress AWS managed policy usage in BucketNotificationsHandler (wildcard for any hash)
  const bucketNotificationHandlers = stack.node.findAll().filter(node =>
    node.node.id.startsWith("BucketNotificationsHandler")
  )

  bucketNotificationHandlers.forEach(handler => {
    safeAddNagSuppression(
      stack,
      `${handler.node.path}/Role/Resource`,
      [
        {
          id: "AwsSolutions-IAM4",
          reason: "Auto-generated CDK role uses AWS managed policy for basic Lambda execution.",
          appliesTo: [
            "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
          ]
        }
      ]
    )

    safeAddNagSuppression(
      stack,
      `${handler.node.path}/Role/DefaultPolicy/Resource`,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "Auto-generated CDK role requires wildcard permissions for S3 bucket notifications.",
          appliesTo: [
            "Resource::*"
          ]
        }
      ]
    )
  })
}

const safeAddNagSuppression = (stack: Stack, path: string, suppressions: Array<NagPackSuppression>) => {
  try {
    NagSuppressions.addResourceSuppressionsByPath(stack, path, suppressions)
  } catch (err) {
    console.log(`Could not find path ${path}: ${err}`)
  }
}
