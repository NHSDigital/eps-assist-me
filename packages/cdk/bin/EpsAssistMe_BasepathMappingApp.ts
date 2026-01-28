import {createApp, getConfigFromEnvVar} from "@nhsdigital/eps-cdk-constructs"
import {EpsAssistMe_BasepathMapping} from "../stacks/EpsAssistMe_BasepathMapping"

async function main() {
  const {app, props} = createApp({
    productName: "EpsAssistMe",
    appName: "EpsAssistMe_Stateless",
    repoName: "eps-assist-me",
    driftDetectionGroup: "epsam",
    isStateless: true
  })

  new EpsAssistMe_BasepathMapping(app, "EpsAssistMeBasepathMapping", {
    ...props,
    statefulStackName: getConfigFromEnvVar("statefulStackName"),
    statelessStackName: getConfigFromEnvVar("statelessStackName")
  })
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
