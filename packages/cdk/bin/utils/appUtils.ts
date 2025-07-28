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
        if (node.logicalId.includes(pattern) && !seen.has(node.logicalId)) {
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
 * Add/merge cfn-guard suppressions to resources for the given rules.
 */
const addSuppressions = (resources: Array<CfnResource>, rules: Array<string>): void => {
  resources.forEach(resource => {
    if (!resource.cfnOptions.metadata) {
      resource.cfnOptions.metadata = {}
    }
    const existing = resource.cfnOptions.metadata.guard?.SuppressedRules || []
    const combined = [...new Set([...existing, ...rules])]
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

  // Suppress S3 bucket guard checks
  const bucketResources = findResourcesByPattern(stack, ["Bucket", "Docs", "Storage"])
  addSuppressions(
    bucketResources,
    [
      "S3_BUCKET_REPLICATION_ENABLED",
      "S3_BUCKET_LOGGING_ENABLED",
      "S3_BUCKET_DEFAULT_LOCK_ENABLED"
    ]
  )

  // Suppress S3 policy guard checks
  const policyResources = findResourcesByPattern(stack, ["Policy", "BucketPolicy"])
  addSuppressions(policyResources, ["S3_BUCKET_SSL_REQUESTS_ONLY"])

  // Suppress API Gateway stage guard checks
  const stageResources = findResourcesByPattern(stack, ["Stage", "DeploymentStage"])
  addSuppressions(stageResources, ["API_GW_CACHE_ENABLED_AND_ENCRYPTED"])
}
