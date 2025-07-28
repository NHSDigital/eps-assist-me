import {Stack, CfnResource} from "aws-cdk-lib"
import {IConstruct} from "constructs"

/**
 * Adds cfn-guard metadata to suppress rules on a resource.
 */
export const addCfnGuardMetadata = (
  stack: Stack,
  path: string,
  childPath?: string,
  suppressedRules: Array<string> = []
) => {
  console.log(`🔍 Looking for construct at path: ${path}${childPath ? "/" + childPath : ""}`)

  const parent = stack.node.tryFindChild(path)
  if (!parent) {
    console.warn(`❌ Could not find path /${stack.stackName}/${path}`)
    // List available children for debugging
    console.log("Available children:", stack.node.children.map(c => c.node.id))
    return
  }

  let target: IConstruct

  if (childPath) {
    const child = parent.node.tryFindChild(childPath)
    if (!child) {
      console.warn(`❌ Could not find path /${stack.stackName}/${path}/${childPath}`)
      // List available children for debugging
      console.log("Available children of parent:", parent.node.children.map(c => c.node.id))
      return
    }
    target = child
  } else {
    target = parent
  }

  let cfnResource: CfnResource | undefined

  if (target instanceof CfnResource) {
    cfnResource = target
  } else if ("defaultChild" in target.node && target.node.defaultChild) {
    const defaultChild = target.node.defaultChild
    if (defaultChild instanceof CfnResource) {
      cfnResource = defaultChild
    }
  }

  if (!cfnResource) {
    console.warn(`⚠️ Target at ${path}${childPath ? "/" + childPath : ""} is not a CfnResource`)
    console.log(`Target type: ${target.constructor.name}`)
    if ("defaultChild" in target.node && target.node.defaultChild) {
      console.log(`Default child type: ${target.node.defaultChild.constructor.name}`)
    }
    return
  }

  // Initialize metadata if it doesn't exist
  if (!cfnResource.cfnOptions.metadata) {
    cfnResource.cfnOptions.metadata = {}
  }

  // Preserve existing guard metadata and merge with new rules
  const existingGuard = cfnResource.cfnOptions.metadata.guard || {}
  const existingSuppressed = existingGuard.SuppressedRules || []
  const allSuppressedRules = [...new Set([...existingSuppressed, ...suppressedRules])]

  cfnResource.cfnOptions.metadata = {
    ...cfnResource.cfnOptions.metadata,
    guard: {
      SuppressedRules: allSuppressedRules
    }
  }

  console.log(`✅ Suppressed rules for ${cfnResource.logicalId}: [${allSuppressedRules.join(", ")}]`)
}
