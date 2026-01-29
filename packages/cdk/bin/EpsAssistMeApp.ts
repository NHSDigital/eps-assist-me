import {
  createApp,
  getBooleanConfigFromEnvVar,
  getConfigFromEnvVar,
  getNumberConfigFromEnvVar
} from "@nhsdigital/eps-cdk-constructs"
import {EpsAssistMe_Stateful} from "../stacks/EpsAssistMe_Stafeful"
import {EpsAssistMe_BasepathMapping} from "../stacks/EpsAssistMe_BasepathMapping"
import {EpsAssistMe_Stateless} from "../stacks/EpsAssistMe_Stateless"
import {applyCfnGuardSuppressions} from "./utils/appUtils"

async function main() {
  const {app, props} = createApp({
    productName: "EpsAssistMe",
    appName: "EpsAssistMe",
    repoName: "eps-assist-me",
    driftDetectionGroup: "epsam",
    isStateless: true
  })

  const statefulStack = new EpsAssistMe_Stateful(app, "EpsAssistMeStateful", {
    ...props,
    region: props.env?.region || "eu-west-2",
    logRetentionInDays: getNumberConfigFromEnvVar("logRetentionInDays"),
    logLevel: getConfigFromEnvVar("logLevel"),
    enableBedrockLogging: getBooleanConfigFromEnvVar("enableBedrockLogging"),
    apiGatewayDomainName: getConfigFromEnvVar("domainName")
  })

  const statelessStack = new EpsAssistMe_Stateless(app, "EpsAssistMeStateless", {
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

  const basePathMapping = new EpsAssistMe_BasepathMapping(app, "EpsAssistMeBasepathMapping", {
    ...props,
    statefulStackName: getConfigFromEnvVar("statefulStackName"),
    statelessStackName: getConfigFromEnvVar("statelessStackName")
  })

  applyCfnGuardSuppressions(statefulStack)
  applyCfnGuardSuppressions(statelessStack)
  applyCfnGuardSuppressions(basePathMapping)

}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
