import {Stack, CfnResource} from "aws-cdk-lib"
import {IConstruct} from "constructs"

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

export const applyCfnGuardSuppressions = (stack: Stack): void => {
  // Lambda suppressions
  const lambdaResources = findResourcesByPattern(stack, [
    "Handler", "Function", "CreateIndex", "SlackBot", "CustomResourceProvider"
  ])
  addSuppressions(lambdaResources, ["LAMBDA_DLQ_CHECK", "LAMBDA_INSIDE_VPC", "LAMBDA_CONCURRENCY_CHECK"])

  // S3 bucket suppressions
  const bucketResources = findResourcesByPattern(stack, ["Bucket", "Docs", "Storage"])
  addSuppressions(bucketResources, ["S3_BUCKET_REPLICATION_ENABLED", "S3_BUCKET_LOGGING_ENABLED"])

  // S3 policy suppressions
  const policyResources = findResourcesByPattern(stack, ["Policy", "BucketPolicy"])
  addSuppressions(policyResources, ["S3_BUCKET_SSL_REQUESTS_ONLY"])

  // API Gateway suppressions
  const stageResources = findResourcesByPattern(stack, ["Stage", "DeploymentStage"])
  addSuppressions(stageResources, ["API_GW_CACHE_ENABLED_AND_ENCRYPTED"])
}
