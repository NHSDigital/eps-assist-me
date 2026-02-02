import {
  calculateVersionedStackName,
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
    driftDetectionGroup: "epsam"
  })

  const statefulStack = new EpsAssistMe_Stateful(app, "EpsAssistMeStateful", {
    ...props,
    stackName: getConfigFromEnvVar("statefulStackName"),
    region: props.env?.region || "eu-west-2",
    logRetentionInDays: getNumberConfigFromEnvVar("logRetentionInDays"),
    logLevel: getConfigFromEnvVar("logLevel"),
    enableBedrockLogging: getBooleanConfigFromEnvVar("enableBedrockLogging"),
    apiGatewayDomainName: getConfigFromEnvVar("domainName")
  })

  const statelessStackName = calculateVersionedStackName(getConfigFromEnvVar("statelessStackName"), props)
  const statelessStack = new EpsAssistMe_Stateless(app, "EpsAssistMeStateless", {
    ...props,
    stackName: statelessStackName,
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
    stackName: getConfigFromEnvVar("basePathMappingStackName"),
    statefulStackName: getConfigFromEnvVar("statefulStackName"),
    statelessStackName: statelessStackName
  })

  applyCfnGuardSuppressions(statefulStack)
  applyCfnGuardSuppressions(statelessStack)
  applyCfnGuardSuppressions(basePathMapping)
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
