import {Stack, CfnResource} from "aws-cdk-lib"
import {IConstruct} from "constructs"

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
 * Find all CfnResources of a specific CloudFormation type.
 */
const findResourcesByType = (construct: IConstruct, type: string): Array<CfnResource> => {
  const matches: Array<CfnResource> = []
  const search = (node: IConstruct): void => {
    if (node instanceof CfnResource && node.cfnResourceType === type) {
      matches.push(node)
    }
    for (const child of node.node.children) {
      search(child)
    }
  }
  search(construct)
  return matches
}

/**
 * Find all CfnResources with a metadata aws:cdk:path that matches any provided path.
 */
const findResourcesByPath = (construct: IConstruct, paths: Array<string>): Array<CfnResource> => {
  const matches: Array<CfnResource> = []
  const targetPaths = new Set(paths)
  const seen = new Set<string>()
  const search = (node: IConstruct): void => {
    if (node instanceof CfnResource) {
      const resourcePath = node.cfnOptions.metadata?.["aws:cdk:path"]
      if (typeof resourcePath === "string" && targetPaths.has(resourcePath) && !seen.has(node.logicalId)) {
        matches.push(node)
        seen.add(node.logicalId)
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
 * Add/merge cfn-guard suppressions to resources for the given rules.
 */
const addSuppressions = (resources: Array<CfnResource>, rules: Array<string>): void => {
  resources.forEach(resource => {
    if (!resource.cfnOptions.metadata) {
      resource.cfnOptions.metadata = {}
    }
    const existing = resource.cfnOptions.metadata.guard?.SuppressedRules || []
    const combined = Array.from(new Set([...existing, ...rules]))
    resource.cfnOptions.metadata.guard = {SuppressedRules: combined}
  })
}

/**
 * Apply cfn-guard suppressions for Lambda, S3, and API Gateway resources.
 */
export const applyCfnGuardSuppressions = (stack: Stack): void => {
  // Suppress all cfn-guard checks for all Lambda functions (including implicit CDK-generated ones)
  const allLambdas = findResourcesByType(stack, "AWS::Lambda::Function")
  addSuppressions(allLambdas, ["LAMBDA_DLQ_CHECK", "LAMBDA_INSIDE_VPC", "LAMBDA_CONCURRENCY_CHECK"])

  const apiGatewayPermissions = findResourcesByPattern(stack, ["ApiPermission"])
  addSuppressions(apiGatewayPermissions, ["LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED"])

  const s3NotificationPermissions = findResourcesByPattern(stack, ["AllowBucketNotifications"])
  addSuppressions(s3NotificationPermissions, ["LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED"])

  const aws_created_resources = findResourcesByPath(stack, [
    "EpsAssistMeStateful/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/LogGroup/Resource",
    "EpsAssistMeStateful/BedrockLogging/LoggingConfigProvider/framework-onEvent/LogGroup/Resource",
    "EpsAssistMeStateful/VectorIndex/IndexReadyWait/DelayProvider/framework-onEvent/LogGroup/Resource",
    "EpsAssistMeStateful/VectorIndex/IndexReadyWait/DelayFunction/LogGroup/Resource",
    "EpsAssistMeStateful/VectorIndex/PolicySyncWait/DelayFunction/LogGroup/Resource",
    "EpsAssistMeStateful/VectorIndex/PolicySyncWait/DelayProvider/framework-onEvent/LogGroup/Resource"
  ])
  addSuppressions(aws_created_resources, ["CLOUDWATCH_LOG_GROUP_ENCRYPTED"])

}
