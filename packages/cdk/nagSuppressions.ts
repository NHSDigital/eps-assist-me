/* eslint-disable max-len, @typescript-eslint/no-unused-vars */
import {Stack} from "aws-cdk-lib"
import {NagPackSuppression, NagSuppressions} from "cdk-nag"

export const nagSuppressions = (stack: Stack) => {
  const stackName = stack.node.tryGetContext("stackName") || "epsam"
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

  // Suppress API Gateway validation warning for Apis construct
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/Apis/EpsAssistApiGatewayPr/ApiGateway/Resource",
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
    "/EpsAssistMeStack/Apis/EpsAssistApiGatewayPr/ApiGateway/Default/slack/ask-eps/POST/Resource",
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
    "/EpsAssistMeStack/Apis/EpsAssistApiGatewayPr/ApiGateway/DeploymentStage.prod/Resource",
    [
      {
        id: "AwsSolutions-APIG3",
        reason: "WAF not in current scope; may be added later."
      }
    ]
  )

  // Suppress IAM wildcard permissions for Bedrock execution managed policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/IamResources/BedrockExecutionManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Bedrock Knowledge Base requires these permissions to access S3 documents and OpenSearch collection.",
        appliesTo: [
          "Action::bedrock:Delete*",
          "Resource::<StorageDocsBucketepsamDocsF25F63F1.Arn>/*",
          "Resource::<StorageDocsBucketepsampr16Docs240CC945.Arn>/*",
          "Resource::arn:aws:bedrock:eu-west-2:undefined:knowledge-base/*",
          "Resource::arn:aws:bedrock:eu-west-2:591291862413:knowledge-base/*",
          "Resource::arn:aws:aoss:eu-west-2:undefined:collection/*",
          "Resource::arn:aws:aoss:eu-west-2:591291862413:collection/*",
          "Resource::*"
        ]
      }
    ]
  )

  // Suppress wildcard permissions for CreateIndex managed policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/IamResources/CreateIndexManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Lambda needs access to all OpenSearch collections and indexes to create and manage indexes.",
        appliesTo: [
          "Resource::arn:aws:aoss:eu-west-2:undefined:collection/*",
          "Resource::arn:aws:aoss:eu-west-2:undefined:index/*",
          "Resource::arn:aws:aoss:eu-west-2:591291862413:collection/*",
          "Resource::arn:aws:aoss:eu-west-2:591291862413:index/*"
        ]
      }
    ]
  )

  // Suppress wildcard permissions for SlackBot managed policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/IamResources/SlackBotManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "SlackBot Lambda needs access to all guardrails, knowledge bases, and functions for content filtering and self-invocation.",
        appliesTo: [
          "Resource::arn:aws:lambda:eu-west-2:undefined:function:*",
          "Resource::arn:aws:lambda:eu-west-2:591291862413:function:*",
          "Resource::arn:aws:bedrock:eu-west-2:undefined:guardrail/*",
          "Resource::arn:aws:bedrock:eu-west-2:591291862413:guardrail/*",
          "Resource::arn:aws:bedrock:eu-west-2:undefined:knowledge-base/*",
          "Resource::arn:aws:bedrock:eu-west-2:591291862413:knowledge-base/*"
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
}

const safeAddNagSuppression = (stack: Stack, path: string, suppressions: Array<NagPackSuppression>) => {
  try {
    NagSuppressions.addResourceSuppressionsByPath(stack, path, suppressions)
  } catch (err) {
    console.log(`Could not find path ${path}: ${err}`)
  }
}

// Apply the same nag suppression to multiple resources
const safeAddNagSuppressionGroup = (stack: Stack, paths: Array<string>, suppressions: Array<NagPackSuppression>) => {
  for (const p of paths) {
    safeAddNagSuppression(stack, p, suppressions)
  }
}
