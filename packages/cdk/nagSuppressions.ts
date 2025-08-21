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
        reason: "Wildcard permissions for log stream access are required and scoped appropriately."
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
        reason: "Wildcard permissions are required for log stream access under known paths."
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

  // Suppress IAM wildcard permissions for Bedrock execution managed policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/IamResources/BedrockExecutionManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Bedrock Knowledge Base requires wildcard permissions to access S3 documents and OpenSearch collection across environments."
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
        reason: "Lambda needs access to all OpenSearch collections and indexes to create and manage indexes."
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
        reason: "SlackBot Lambda needs wildcard permissions for guardrails, knowledge bases, and function invocation."
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
  safeAddNagSuppressionGroup(
    stack,
    [
      "/EpsAssistMeStack/Secrets/SlackBotToken/Secret/Resource",
      "/EpsAssistMeStack/Secrets/SlackBotSigning/Secret/Resource"
    ],
    [
      {
        id: "AwsSolutions-SMG4",
        reason: "Slack secrets rotation is handled manually as part of the Slack app configuration process."
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
