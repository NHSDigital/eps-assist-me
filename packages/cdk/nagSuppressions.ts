
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
        reason: "Bedrock Knowledge Base requires these permissions to access S3 documents and OpenSearch collection."
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
        reason: "Lambda needs access to all OpenSearch collections and indexes to create and manage indexes."
      }
    ]
  )

  // Suppress IAM wildcard permissions for waiter function execution role policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/SlackBotLambda/LambdaPutLogsManagedPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Lambda needs access to all OpenSearch collections and indexes to create and manage indexes."
      }
    ]
  )

  // Suppress IAM wildcard permissions for waiter on event role policy
  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/IndexWaiterProvider/framework-onEvent/ServiceRole/DefaultPolicy/Resource",
    [
      {
        id: "AwsSolutions-IAM5",
        reason: "Lambda needs access to all OpenSearch collections and indexes to create and manage indexes."
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

  safeAddNagSuppression(
    stack,
    "/EpsAssistMeStack/VectorIndex/IndexWaiterProvider/framework-onEvent/ServiceRole/Resource",
    [
      {
        id: "AwsSolutions-IAM4",
        reason: "Waiter function on event using managed policies is fine"
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

    // TO REMOVE
    safeAddNagSuppression(
      stack,
      "EpsAssistMeStack/VectorIndex/waiterFnManagedPolicy/Resource",
      [
        {
          id: "AwsSolutions-IAM5",
          reason: "Auto-generated CDK role requires wildcard permissions for S3 bucket notifications."
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

const safeAddNagSuppressionGroup = (stack: Stack, paths: Array<string>, suppressions: Array<NagPackSuppression>) => {
  paths.forEach(path => safeAddNagSuppression(stack, path, suppressions))
}
