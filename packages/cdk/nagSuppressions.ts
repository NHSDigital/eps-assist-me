import {Stack} from "aws-cdk-lib"
import {NagPackSuppression, NagSuppressions} from "cdk-nag"

export const nagSuppressions = (stack: Stack) => {
  safeAddNagSuppressionGroup(
    stack,
    [
      "/EpsAssistMeStack/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/DefaultPolicy/Resource",
      "/EpsAssistMeStack/SlackBotLambda/SlackBotFunctionPutLogsPolicy/Resource"
    ],
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Wildcard permissions are required for log stream access under known paths."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistApiGateway/RestApi/Resource",
    [
      {
        id: "AwsSolutions-APIG2",
        reason: "Validation is handled within Lambda; request validation is intentionally omitted."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/Resource",
    [
      {
        id: "AwsSolutions-IAM4",
        reason: "Auto-generated service role uses AWS managed policy, which is acceptable here."
      }
    ]
  )

  safeAddNagSuppressionGroup(
    stack,
    [
      "/EpsAssistMeStack/EpsAssistApiGateway/RestApi/Default/slack/ask-eps/POST/Resource"
    ],
    [
      {
        id: "AwsSolutions-APIG4",
        reason: "Slack command endpoint is intentionally unauthenticated."
      },
      {
        id: "AwsSolutions-COG4",
        reason: "Cognito authorizer is not required for public Slack integration endpoint."
      }
    ]
  )

  // 🔒 Suppress missing S3 access logs (AwsSolutions-S1)
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistDocsBucket/Resource",
    [
      {
        id: "AwsSolutions-S1",
        reason: "Access logs not required for internal, ephemeral S3 usage during development."
      },
      {
        id: "AwsSolutions-S10",
        reason: "Bucket policy enforcing SSL is not yet implemented but tracked for future."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistDocsBucket/Policy/Resource",
    [
      {
        id: "AwsSolutions-S10",
        reason: "Bucket policy lacks aws:SecureTransport condition; known and acceptable short-term."
      }
    ]
  )

  // 🛡️ Suppress lack of WAF on API Gateway stage
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistApiGateway/RestApi/DeploymentStage.prod/Resource",
    [
      {
        id: "AwsSolutions-APIG3",
        reason: "WAF integration is not part of the current scope but may be added later."
      }
    ]
  )

  // ⚠️ Suppress non-latest Lambda runtime
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/SlackBotLambda/SlackBotFunction/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "Using specific Python runtime version pinned intentionally for compatibility."
      }
    ]
  )
}

const safeAddNagSuppression = (stack: Stack, path: string, suppressions: Array<NagPackSuppression>) => {
  try {
    NagSuppressions.addResourceSuppressionsByPath(stack, path, suppressions)
  } catch (err) {
    console.log(`Could not find path ${path}`)
  }
}

const safeAddNagSuppressionGroup = (stack: Stack, paths: string[], suppressions: Array<NagPackSuppression>) => {
  for (const path of paths) {
    safeAddNagSuppression(stack, path, suppressions)
  }
}
