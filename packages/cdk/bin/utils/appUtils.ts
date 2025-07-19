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
  const parent = stack.node.tryFindChild(path)
  if (!parent) {
    console.warn(`Could not find path /${stack.stackName}/${path}`)
    return
  }

  let target: IConstruct

  if (childPath) {
    const child = parent.node.tryFindChild(childPath)
    if (!child) {
      console.warn(`Could not find path /${stack.stackName}/${path}/${childPath}`)
      return
    }
    target = child
  } else {
    target = parent
  }

  let cfnResource: CfnResource | undefined

  if (target instanceof CfnResource) {
    cfnResource = target
  } else if ("defaultChild" in target.node) {
    const defaultChild = target.node.defaultChild
    if (defaultChild instanceof CfnResource) {
      cfnResource = defaultChild
    }
  }

  if (!cfnResource) {
    console.warn(`⚠️ Target at ${path}${childPath ? "/" + childPath : ""} is not a CfnResource`)
    return
  }

  cfnResource.cfnOptions.metadata = {
    ...cfnResource.cfnOptions.metadata,
    guard: {
      SuppressedRules: suppressedRules
    }
  }

  console.log(`✅ Suppressed rules for ${cfnResource.logicalId}: [${suppressedRules.join(", ")}]`)
}
