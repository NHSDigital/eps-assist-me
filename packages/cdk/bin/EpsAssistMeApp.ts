#!/usr/bin / env node
import {App, Aspects, Tags} from "aws-cdk-lib"
import {AwsSolutionsChecks} from "cdk-nag"
import {EpsAssistMeStack} from "../stacks/EpsAssistMeStack"
import {addCfnGuardMetadata} from "./utils/appUtils"

const app = new App()

/* Required Context:
- accountId
- stackName
- version
- commit
*/

const accountId = app.node.tryGetContext("accountId")
const stackName = app.node.tryGetContext("stackName")
const version = app.node.tryGetContext("versionNumber")
const commit = app.node.tryGetContext("commitId")

Aspects.of(app).add(new AwsSolutionsChecks({verbose: true}))

Tags.of(app).add("cdkApp", "EpsAssistMe")
Tags.of(app).add("accountId", accountId)
Tags.of(app).add("stackName", stackName)
Tags.of(app).add("version", version)
Tags.of(app).add("commit", commit)

console.log("CDK context:", {accountId, stackName, version, commit})

if (!accountId || !stackName || !version || !commit) {
  throw new Error(`Missing required CDK context values: ${JSON.stringify({accountId, stackName, version, commit})}`)
}

const EpsAssistMe = new EpsAssistMeStack(app, "EpsAssistMeStack", {
  env: {
    region: "eu-west-2",
    account: accountId
  },
  stackName: stackName,
  version: version,
  commitId: commit
})

// Run a synth to add cross region lambdas and roles
app.synth()

// Add metadata to lambda so they don't get flagged as failing cfn-guard
addCfnGuardMetadata(EpsAssistMe, "AWS679f53fac002430cb0da5b7982bd2287", "Resource")
addCfnGuardMetadata(EpsAssistMe, "EpsAssistAccessLogsBucket", "Resource",
  ["S3_BUCKET_LOGGING_ENABLED", "S3_BUCKET_SSL_REQUESTS_ONLY"]
)

// Finally run synth again with force to include the added metadata
app.synth({
  force: true
})
