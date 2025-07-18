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
  safeAddNagSuppressionGroup(
    stack,
    [
      "/EpsAssistMeStack/CreateIndexFunction/CreateIndexFunctionPutLogsPolicy/Resource",
      "/EpsAssistMeStack/CreateIndexFunction/LambdaPutLogsManagedPolicy/Resource"
    ],
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

  // Suppress AWS managed policy warning for default CDK log retention resource
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

  // Suppress unauthenticated API Gateway route warnings
  safeAddNagSuppressionGroup(
    stack,
    [
      "/EpsAssistMeStack/EpsAssistApiGateway/ApiGateway/Default/slack/ask-eps/POST/Resource"
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

  // Suppress missing S3 access logs and lack of SSL on EpsAssistDocsBucket
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
      },
      {
        id: "S3_BUCKET_REPLICATION_ENABLED",
        reason: "Replication not needed for internal documentation bucket."
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

  // Suppress lack of WAF on API Gateway stage
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistApiGateway/ApiGateway/DeploymentStage.prod/Resource",
    [
      {
        id: "AwsSolutions-APIG3",
        reason: "WAF integration is not part of the current scope but may be added later."
      }
    ]
  )

  // Suppress non-latest Lambda runtime
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/SlackBotLambda/SlackBotFunction/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "Using specific Python runtime version pinned intentionally for compatibility."
      },
      {
        id: "LAMBDA_DLQ_CHECK",
        reason: "DLQ setup pending; tracked in backlog."
      },
      {
        id: "LAMBDA_INSIDE_VPC",
        reason: "VPC config setup pending; tracked in backlog."
      }
    ]
  )

  // DLQ for CreateIndexFunction missing aws:SecureTransport
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/CreateIndexFunction/CreateIndexFunctionDLQ/Resource",
    [
      {
        id: "AwsSolutions-SQS4",
        reason: "DLQ is used internally and SSL policy enforcement is deferred."
      }
    ]
  )

  // DLQ for SlackBotFunction missing aws:SecureTransport
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/SlackBotLambda/SlackBotFunctionDLQ/Resource",
    [
      {
        id: "AwsSolutions-SQS4",
        reason: "DLQ is used internally and SSL policy enforcement is deferred."
      }
    ]
  )

  // Missing replication/versioning/logging/ssl on access log bucket
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistAccessLogsBucket/Resource",
    [
      {
        id: "AwsSolutions-S10",
        reason: "Access logs bucket is internal and SSL enforcement is deferred to future hardening."
      },
      {
        id: "S3_BUCKET_REPLICATION_ENABLED",
        reason: "Replication not required for ephemeral access log storage."
      },
      {
        id: "S3_BUCKET_VERSIONING_ENABLED",
        reason: "Versioning not necessary on log bucket; data is short-lived."
      },
      {
        id: "S3_BUCKET_LOGGING_ENABLED",
        reason: "Access log bucket logging is circular and not required."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/EpsAssistAccessLogsBucket/Policy/Resource",
    [
      {
        id: "AwsSolutions-S10",
        reason: "Access logs bucket policy does not yet enforce SSL; tracked for future improvement."
      }
    ]
  )

  // Custom resource Lambda for S3 auto-delete lacks DLQ and VPC
  safeAddNagSuppressionGroup(
    stack,
    [
      "/EpsAssistMeStack/Custom::S3AutoDeleteObjectsCustomResourceProvider/Handler"
    ],
    [
      {
        id: "LAMBDA_DLQ_CHECK",
        reason: "Custom resource handler is AWS-managed; DLQ is not configurable."
      },
      {
        id: "LAMBDA_INSIDE_VPC",
        reason: "VPC configuration not applicable for AWS-managed custom resource Lambda."
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
const safeAddNagSuppressionGroup = (stack: Stack, path: Array<string>, suppressions: Array<NagPackSuppression>) => {
  for (const p of path) {
    safeAddNagSuppression(stack, p, suppressions)
  }
}
