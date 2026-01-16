/* eslint-disable max-len */

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

  // Suppress wildcard log permissions for SyncKnowledgeBase Lambda
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/Functions/SyncKnowledgeBaseFunction/LambdaPutLogsManagedPolicy/Resource",
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

  // Suppress unauthenticated API route warnings
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/Apis/EpsAssistApiGateway/ApiGateway/Default/slack/events/POST/Resource",
    [
      {
        id: "AwsSolutions-APIG4",
        reason: "Slack event endpoint is intentionally unauthenticated."
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
          "Action::bedrock:Delete*",
          "Resource::arn:aws:bedrock:eu-west-2:<AWS::AccountId>:knowledge-base/*",
          "Resource::arn:aws:aoss:eu-west-2:<AWS::AccountId>:collection/*",
          "Resource::arn:aws:logs:eu-west-2:<AWS::AccountId>:delivery-destination:*",
          "Resource::arn:aws:logs:eu-west-2:<AWS::AccountId>:delivery-source:*",
          "Resource::arn:aws:logs:eu-west-2:<AWS::AccountId>:delivery:*"
        ]
      }
    ]
  )
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/BedrockExecutionRole/WildcardPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Bedrock Knowledge Base requires these wildcard permissions to access S3 documents and OpenSearch collection."
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
        reason: "SlackBot Lambda needs wildcard permissions for guardrails, knowledge bases, and function invocation.",
        appliesTo: [
          "Resource::arn:aws:lambda:eu-west-2:<AWS::AccountId>:function:epsam*",
          "Resource::arn:aws:cloudformation:eu-west-2:<AWS::AccountId>:stack/epsam-pr-*",
          "Resource::arn:aws:bedrock:*"
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
          reason: "Auto-generated CDK role uses AWS managed policy for basic Lambda execution."
        }
      ]
    )

    safeAddNagSuppression(
      stack,
      `${handler.node.path}/Role/DefaultPolicy/Resource`,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "Auto-generated CDK role requires wildcard permissions for S3 bucket notifications."
        }
      ]
    )
  })

  const logRetentionHandlers = stack.node.findAll().filter(node =>
    node.node.id.startsWith("LogRetention") &&
    !node.node.path.includes("DelayProvider")
  )

  logRetentionHandlers.forEach(handler => {
    safeAddNagSuppression(
      stack,
      `${handler.node.path}/ServiceRole/Resource`,
      [
        {
          id: "AwsSolutions-IAM4",
          reason: "Auto-generated CDK log retention role uses AWS managed policy for basic Lambda execution."
        }
      ]
    )

    safeAddNagSuppression(
      stack,
      `${handler.node.path}/ServiceRole/DefaultPolicy/Resource`,
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "Auto-generated CDK log retention role requires wildcard permissions for log management."
        }
      ]
    )
  })

  // Suppress DelayResource IAM and runtime issues
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/PolicySyncWait/LambdaExecutionRole/Resource",
    [
      {
        id: "AwsSolutions-IAM4",
        reason: "DelayResource Lambda uses AWS managed policy for basic Lambda execution role."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/IndexReadyWait/LambdaExecutionRole/Resource",
    [
      {
        id: "AwsSolutions-IAM4",
        reason: "DelayResource Lambda uses AWS managed policy for basic Lambda execution role."
      }
    ]
  )

  // Suppress DelayProvider framework ServiceRole issues
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/PolicySyncWait/DelayProvider/framework-onEvent/ServiceRole/Resource",
    [
      {
        id: "AwsSolutions-IAM4",
        reason: "Auto-generated CDK Provider role uses AWS managed policy for Lambda execution."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/PolicySyncWait/DelayProvider/framework-onEvent/ServiceRole/DefaultPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Auto-generated CDK Provider role requires wildcard permissions for Lambda invocation."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/IndexReadyWait/DelayProvider/framework-onEvent/ServiceRole/Resource",
    [
      {
        id: "AwsSolutions-IAM4",
        reason: "Auto-generated CDK Provider role uses AWS managed policy for Lambda execution."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/IndexReadyWait/DelayProvider/framework-onEvent/ServiceRole/DefaultPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Auto-generated CDK Provider role requires wildcard permissions for Lambda invocation."
      }
    ]
  )

  // Suppress DelayFunction runtime version warnings
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/PolicySyncWait/DelayFunction/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "DelayResource uses Python 3.12 which is the latest stable runtime available for the delay functionality."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/IndexReadyWait/DelayFunction/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "DelayResource uses Python 3.12 which is the latest stable runtime available for the delay functionality."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/RegressionTestPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Auto-generated CDK Provider role requires wildcard permissions for cloudformation stack listing."
      }
    ]
  )

  // suppress onEvent runtime warnings as this is managed by the CDK team
  // see https://github.com/aws/aws-cdk/issues/36269 for issue raised with CDK team
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/PolicySyncWait/DelayProvider/framework-onEvent/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "OnEvent uses Node22.x which is the latest stable runtime available for the onEvent functionality."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/IndexReadyWait/DelayProvider/framework-onEvent/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "OnEvent uses Node22.x which is the latest stable runtime available for the onEvent functionality."
      }
    ]
  )

  // Suppress BedrockLogging KMS wildcard permissions
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/BedrockLogging/BedrockLoggingRole/DefaultPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "KMS wildcard permissions (GenerateDataKey*, ReEncrypt*) are required for CloudWatch Logs encryption operations."
      }
    ]
  )

  // Suppress BedrockLogging Lambda wildcard permissions for Bedrock API
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/BedrockLogging/BedrockLoggingConfigPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Bedrock logging configuration API requires wildcard resource permissions as it's account-level configuration."
      }
    ]
  )

  // Suppress BedrockLogging Lambda log group and put logs permissions
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/BedrockLogging/LoggingConfigFunction/LambdaPutLogsManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Wildcard permissions for log stream access are required and scoped appropriately."
      }
    ]
  )

  // Suppress BedrockLogging Provider framework role using AWS managed policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/BedrockLogging/LoggingConfigProvider/framework-onEvent/ServiceRole/Resource",
    [
      {
        id: "AwsSolutions-IAM4",
        reason: "Auto-generated CDK Provider role uses AWS managed policy for Lambda execution."
      }
    ]
  )

  // Suppress BedrockLogging Provider framework wildcard permissions
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/BedrockLogging/LoggingConfigProvider/framework-onEvent/ServiceRole/DefaultPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Auto-generated CDK Provider role requires wildcard permissions for Lambda invocation."
      }
    ]
  )

  // Suppress BedrockLogging Provider framework runtime version
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/BedrockLogging/LoggingConfigProvider/framework-onEvent/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "OnEvent uses Node22.x which is the latest stable runtime available for the onEvent functionality."
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

const safeAddNagSuppressionGroup = (stack: Stack, paths: Array<string>, suppressions: Array<NagPackSuppression>) => {
  paths.forEach(path => safeAddNagSuppression(stack, path, suppressions))
}
