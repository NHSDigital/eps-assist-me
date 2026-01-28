import {createApp, getConfigFromEnvVar} from "@nhsdigital/eps-cdk-constructs"
import {EpsAssistMe_BasepathMapping} from "../stacks/EpsAssistMe_BasepathMapping"

async function main() {
  const driftDetectionGroup = getConfigFromEnvVar("cfnDriftDetectionGroup")
  const {app, props} = createApp({
    productName: "EpsAssistMe",
    appName: "EpsAssistMe_Stateless",
    repoName: "eps-assist-me",
    driftDetectionGroup: driftDetectionGroup,
    isStateless: true
  })

  new EpsAssistMe_BasepathMapping(app, "EpsAssistMeStateful", {
    ...props,
    domainImport: getConfigFromEnvVar("domainImport"),
    apiGatewayId: getConfigFromEnvVar("apiGatewayId")
  })
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
