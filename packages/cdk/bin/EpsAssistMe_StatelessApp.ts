import {
  createApp,
  getBooleanConfigFromEnvVar,
  getConfigFromEnvVar,
  getNumberConfigFromEnvVar
} from "@nhsdigital/eps-cdk-constructs"
import {EpsAssistMe_Stateless} from "../stacks/EpsAssistMe_Stateless"

async function main() {
  const {app, props} = createApp({
    productName: "EpsAssistMe",
    appName: "EpsAssistMe_Stateless",
    repoName: "eps-assist-me",
    driftDetectionGroup: "epsam",
    isStateless: true
  })

  new EpsAssistMe_Stateless(app, "EpsAssistMeStateless", {
    ...props,
    region: props.env?.region || "eu-west-2",
    logRetentionInDays: getNumberConfigFromEnvVar("logRetentionInDays"),
    logLevel: getConfigFromEnvVar("logLevel"),
    runRegressionTests: getBooleanConfigFromEnvVar("runRegressionTests"),
    forwardCsocLogs: getBooleanConfigFromEnvVar("forwardCsocLogs"),
    // eslint-disable-next-line max-len
    csocApiGatewayDestination: "arn:aws:logs:eu-west-2:693466633220:destination:api_gateway_log_destination", // CSOC API GW log destination - do not change
    slackBotToken: getConfigFromEnvVar("slackBotToken"),
    slackSigningSecret: getConfigFromEnvVar("slackSigningSecret"),
    statefulStackName: getConfigFromEnvVar("statefulStackName")
  })
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
