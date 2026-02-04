import {Stack, CfnResource} from "aws-cdk-lib"
import {IConstruct} from "constructs"
import {
  addLambdaCfnGuardSuppressions,
  findCloudFormationResourcesByPath,
  addSuppressions
} from "@nhsdigital/eps-cdk-constructs"

/**
 * Find all CfnResources whose logicalId matches any provided pattern.
 */
const findResourcesByPattern = (construct: IConstruct, patterns: Array<string>): Array<CfnResource> => {
  const matches: Array<CfnResource> = []
  const seen = new Set<string>()
  const search = (node: IConstruct): void => {
    if (node instanceof CfnResource) {
      for (const pattern of patterns) {
        if (node.node.id.includes(pattern) && !seen.has(node.logicalId)) {
          matches.push(node)
          seen.add(node.logicalId)
          break
        }
      }
    }
    for (const child of node.node.children) {
      search(child)
    }
  }
  search(construct)
  return matches
}

/**
 * Apply cfn-guard suppressions for Lambda, S3, and API Gateway resources.
 */
export const applyCfnGuardSuppressions = (stack: Stack): void => {
  // Suppress all cfn-guard checks for all Lambda functions (including implicit CDK-generated ones)
  addLambdaCfnGuardSuppressions(stack)
  const apiGatewayPermissions = findResourcesByPattern(stack, ["ApiPermission"])
  addSuppressions(apiGatewayPermissions, ["LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED"])

  const s3NotificationPermissions = findResourcesByPattern(stack, ["AllowBucketNotifications"])
  addSuppressions(s3NotificationPermissions, ["LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED"])

  const aws_created_resources = findCloudFormationResourcesByPath(stack, [
    "EpsAssistMeStateful/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/LogGroup/Resource",
    "EpsAssistMeStateful/BedrockLogging/LoggingConfigProvider/framework-onEvent/LogGroup/Resource",
    "EpsAssistMeStateful/VectorIndex/IndexReadyWait/DelayProvider/framework-onEvent/LogGroup/Resource",
    "EpsAssistMeStateful/VectorIndex/IndexReadyWait/DelayFunction/LogGroup/Resource",
    "EpsAssistMeStateful/VectorIndex/PolicySyncWait/DelayFunction/LogGroup/Resource",
    "EpsAssistMeStateful/VectorIndex/PolicySyncWait/DelayProvider/framework-onEvent/LogGroup/Resource"
  ])
  addSuppressions(aws_created_resources, ["CLOUDWATCH_LOG_GROUP_ENCRYPTED"])

}
