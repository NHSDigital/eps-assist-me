/* eslint-disable max-len */

import {Stack} from "aws-cdk-lib"
import {safeAddNagSuppressionGroup, safeAddNagSuppression} from "@nhsdigital/eps-cdk-constructs"

export const statefulNagSuppressions = (stack: Stack, account: string) => {
  // Suppress wildcard log permissions for SyncKnowledgeBase Lambda
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/StatefulFunctions/SyncKnowledgeBaseFunction/LambdaPutLogsManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Wildcard permissions are required for log stream access under known paths."
      }
    ]
  )

  // Suppress wildcard log permissions for Preprocessing Lambda
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/StatefulFunctions/PreprocessingFunction/LambdaPutLogsManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Wildcard permissions are required for log stream access under known paths."
      }
    ]
  )

  // Suppress IAM wildcard permissions for Bedrock execution role policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/BedrockExecutionRole/Policy/Resource",
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
          "Resource::arn:aws:logs:eu-west-2:<AWS::AccountId>:delivery:*",
          `Resource::arn:aws:bedrock:eu-west-2:${account}:knowledge-base/*`,
          `Resource::arn:aws:aoss:eu-west-2:${account}:collection/*`,
          `Resource::arn:aws:logs:eu-west-2:${account}:delivery-destination:*`,
          `Resource::arn:aws:logs:eu-west-2:${account}:delivery-source:*`,
          `Resource::arn:aws:logs:eu-west-2:${account}:delivery:*`
        ]
      }
    ]
  )
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/BedrockExecutionRole/WildcardPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Bedrock Knowledge Base requires these wildcard permissions to access S3 documents and OpenSearch collection."
      }
    ]
  )

  // Suppress wildcard permissions for Preprocessing policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/StatefulRuntimePolicies/PreprocessingPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Preprocessing Lambda needs wildcard permissions to read/write any file in raw/ and processed/ prefixes."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole/DefaultPolicy/Resource",
    [
      {
        id: "EpsNagPack-EPS10",
        reason: "Role created by CDK lib uses inline policies."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/ApiDomainName/ApiDomain/Resource",
    [
      {
        id: "EpsNagPack-EPS1",
        reason: "API Gateway does not have mutual TLS in this application."
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
          appliesTo: ["Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
        }
      ]
    )
  })

  // Suppress DelayFunction runtime version warnings
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/VectorIndex/PolicySyncWait/epsam-stateful-policy-sync-waitDelayFunction/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "DelayResource uses Python 3.12 which is the latest stable runtime available for the delay functionality."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/VectorIndex/IndexReadyWait/epsam-stateful-index-ready-waitDelayFunction/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "DelayResource uses Python 3.12 which is the latest stable runtime available for the delay functionality."
      }
    ]
  )

  // suppress onEvent runtime warnings as this is managed by the CDK team
  // see https://github.com/aws/aws-cdk/issues/36269 for issue raised with CDK team
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/VectorIndex/PolicySyncWait/epsam-stateful-policy-sync-waitDelayProvider/framework-onEvent/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "OnEvent uses Node22.x which is the latest stable runtime available for the onEvent functionality."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/VectorIndex/IndexReadyWait/epsam-stateful-index-ready-waitDelayProvider/framework-onEvent/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "OnEvent uses Node22.x which is the latest stable runtime available for the onEvent functionality."
      }
    ]
  )

  // Suppress BucketDeployment (S3 folder initializer) suppressions
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole/Resource",
    [
      {
        id: "AwsSolutions-IAM4",
        reason: "BucketDeployment uses AWS managed policy for Lambda execution, required by CDK construct.",
        appliesTo: ["Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
      }
    ]
  )

  // Suppress BedrockLogging Lambda wildcard permissions for Bedrock API
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/BedrockLogging/BedrockLoggingConfigPolicy/Resource",
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
    "/EpsAssistMeStateful/BedrockLogging/LoggingConfigFunction/LambdaPutLogsManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Wildcard permissions for log stream access are required and scoped appropriately."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole/DefaultPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "BucketDeployment requires wildcard permissions for S3 and KMS operations to deploy assets."
      }
    ]
  )

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "BucketDeployment uses CDK-managed Lambda runtime, updated by CDK library."
      }
    ]
  )

  // Suppress BedrockLogging Provider framework runtime version
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/BedrockLogging/LoggingConfigProvider/framework-onEvent/Resource",
    [
      {
        id: "AwsSolutions-L1",
        reason: "OnEvent uses Node22.x which is the latest stable runtime available for the onEvent functionality."
      }
    ]
  )

  // Suppress BedrockLogging Provider framework runtime version
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/BucketNotificationsHandler050a0587b7544547bf325f094a3db834/Role/DefaultPolicy/Resource",
    [
      {
        id: "EpsNagPack-EPS10",
        reason: "Bucket notification role uses inline policies."
      }
    ]
  )

  // Suppress BedrockLogging Provider framework runtime version
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateful/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/LogGroup/Resource",
    [
      {
        id: "EpsNagPack-EPS3",
        reason: "Cloudwatch log group for bucket sync not encrypted by KMS."
      }
    ]
  )
}

export const statelessNagSuppressions = (stack: Stack, account: string) => {
  // Suppress granular wildcard on log stream for SlackBot Lambda
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateless/Functions/SlackBotLambda/LambdaPutLogsManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Wildcard permissions for log stream access are required and scoped appropriately."
      }
    ]
  )

  // Suppress API Gateway validation warning for Apis construct
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateless/Apis/EpsAssistApiGateway/ApiGateway/Resource",
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
    "/EpsAssistMeStateless/Apis/EpsAssistApiGateway/ApiGateway/Default/slack/events/POST/Resource",
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
    "/EpsAssistMeStateless/Apis/EpsAssistApiGateway/ApiGateway/DeploymentStage.prod/Resource",
    [
      {
        id: "AwsSolutions-APIG3",
        reason: "WAF not in current scope; may be added later."
      }
    ]
  )

  // Suppress wildcard permissions for SlackBot policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStateless/RuntimePolicies/SlackBotPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "SlackBot Lambda needs wildcard permissions for guardrails, knowledge bases, and function invocation.",
        appliesTo: [
          "Resource::arn:aws:lambda:eu-west-2:<AWS::AccountId>:function:epsam*",
          "Resource::arn:aws:cloudformation:eu-west-2:<AWS::AccountId>:stack/epsam-pr-*",
          `Resource::arn:aws:lambda:eu-west-2:${account}:function:epsam*`,
          `Resource::arn:aws:cloudformation:eu-west-2:${account}:stack/epsam-pr-*`,
          "Resource::arn:aws:bedrock:*"
        ]
      }
    ]
  )

  // Suppress secrets without rotation
  safeAddNagSuppressionGroup(
    stack,
    [
      "/EpsAssistMeStateless/Secrets/SlackBotToken/Secret/Resource",
      "/EpsAssistMeStateless/Secrets/SlackBotSigning/Secret/Resource"
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
    "/EpsAssistMeStateless/RegressionTestPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Auto-generated CDK Provider role requires wildcard permissions for cloudformation stack listing.",
        appliesTo: [
          "Resource::arn:aws:cloudformation:eu-west-2:<AWS::AccountId>:stack/epsam*",
          `Resource::arn:aws:cloudformation:eu-west-2:${account}:stack/epsam*`
        ]
      }
    ]
  )

}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const basePathMappingNagSuppressions = (stack: Stack, account: string) => {}
