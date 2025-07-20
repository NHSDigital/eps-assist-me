/* eslint-disable max-len */
import {Stack} from "aws-cdk-lib"
import {NagPackSuppression, NagSuppressions} from "cdk-nag"

export const nagSuppressions = (stack: Stack) => {
  // Suppress granular wildcard on log stream for SlackBot Lambda
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/SlackBotLambda/LambdaPutLogsManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Wildcard permissions for log stream access are required and scoped appropriately.",
        appliesTo: [
          "Resource::<SlackBotLambdaLambdaLogGroup7AD7BC9E.Arn>:log-stream:*"
        ]
      }
    ]
  )

  // Suppress wildcard log permissions for CreateIndex Lambda
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/CreateIndexFunction/LambdaPutLogsManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Wildcard permissions are required for log stream access under known paths."
      }
    ]
  )

  // Suppress API Gateway validation warning
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistApiGateway/ApiGateway/Resource",
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
  safeAddNagSuppressionGroup(
    stack,
    ["/EpsAssistMeStack/EpsAssistApiGateway/ApiGateway/Default/slack/ask-eps/POST/Resource"],
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

  // Suppress S3 warnings on EpsAssistDocsBucket
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistDocsBucket/Resource",
    [
      {
        id: "AwsSolutions-S1",
        reason: "No access logs needed for internal development usage."
      },
      {
        id: "AwsSolutions-S10",
        reason: "SSL enforcement via bucket policy is deferred."
      },
      {
        id: "S3_BUCKET_REPLICATION_ENABLED",
        reason: "Replication not required for internal bucket."
      }
    ]
  )

  // Suppress SSL requirement on Docs bucket policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/KbDocsTlsPolicy",
    [
      {
        id: "AwsSolutions-S10",
        reason: "SSL enforcement for docs bucket policy is deferred; tracked for future hardening."
      }
    ]
  )

  // Suppress missing WAF on API stage
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistApiGateway/ApiGateway/DeploymentStage.prod/Resource",
    [
      {
        id: "AwsSolutions-APIG3",
        reason: "WAF not in current scope; may be added later."
      }
    ]
  )

  // Suppress warnings on access logs bucket
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistAccessLogsBucket/Resource",
    [
      {
        id: "AwsSolutions-S10",
        reason: "SSL policy is pending; logged for follow-up."
      },
      {
        id: "S3_BUCKET_REPLICATION_ENABLED",
        reason: "Replication not needed."
      },
      {
        id: "S3_BUCKET_VERSIONING_ENABLED",
        reason: "Short-lived logs don't need versioning."
      },
      {
        id: "S3_BUCKET_LOGGING_ENABLED",
        reason: "No logging needed on logging bucket."
      }
    ]
  )

  // Suppress SSL enforcement warning on AccessLogs bucket TLS policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/AccessLogsBucketTlsPolicy",
    [
      {
        id: "AwsSolutions-S10",
        reason: "SSL enforcement for access logs bucket TLS policy is deferred; tracked for future hardening."
      }
    ]
  )

  // Suppress SSL warning on actual access log bucket policy resource
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistAccessLogsBucket/Policy/Resource",
    [
      {
        id: "AwsSolutions-S10",
        reason: "SSL enforcement on access logs bucket policy is deferred and documented."
      }
    ]
  )

  // Suppress wildcard and granular permissions for Bedrock execution role
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistMeBedrockExecutionRole/DefaultPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason:
          "Bedrock execution role requires wildcard and resource-wide permissions for access to S3 bucket and AOSS. Permissions are scoped to specific resources where possible; further scoping is tracked for future hardening.",
        appliesTo: [
          "Resource::<EpsAssistDocsBucketD6886E55.Arn>/*",
          "Resource::<OsCollection.Arn>/*",
          "Action::aoss:*",
          "Resource::*"
        ]
      }
    ]
  )
}

const safeAddNagSuppression = (stack: Stack, path: string, suppressions: Array<NagPackSuppression>) => {
  try {
    NagSuppressions.addResourceSuppressionsByPath(stack, path, suppressions)
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
  } catch (err) {
    console.log(`Could not find path ${path}`)
  }
}

// Apply the same nag suppression to multiple resources
const safeAddNagSuppressionGroup = (stack: Stack, paths: Array<string>, suppressions: Array<NagPackSuppression>) => {
  for (const p of paths) {
    safeAddNagSuppression(stack, p, suppressions)
  }
}
