import {
  createApp,
  getBooleanConfigFromEnvVar,
  getConfigFromEnvVar,
  getNumberConfigFromEnvVar
} from "@nhsdigital/eps-cdk-constructs"
import {EpsAssistMe_Stateful} from "../stacks/EpsAssistMe_Stafeful"

async function main() {
  const {app, props} = createApp({
    productName: "EpsAssistMe",
    appName: "EpsAssistMe_Stateless",
    repoName: "eps-assist-me",
    driftDetectionGroup: getConfigFromEnvVar("cfnDriftDetectionGroup"),
    isStateless: true
  })

  new EpsAssistMe_Stateful(app, "EpsAssistMeStateful", {
    ...props,
    region: props.env?.region || "eu-west-2",
    logRetentionInDays: getNumberConfigFromEnvVar("logRetentionInDays"),
    logLevel: getConfigFromEnvVar("logLevel"),
    enableBedrockLogging: getBooleanConfigFromEnvVar("enableBedrockLogging")
  })
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
