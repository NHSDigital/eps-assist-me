#!/usr/bin / env node
import {App, Aspects, Tags} from "aws-cdk-lib"
import {AwsSolutionsChecks} from "cdk-nag"
import {EpsAssistMeStack} from "../stacks/EpsAssistMeStack"

const app = new App()

/* Required Context:
- accountId
- stackName
- version
- commit
- logRetentionInDays
- logLevel
*/

const accountId = app.node.tryGetContext("accountId")
const stackName = app.node.tryGetContext("stackName")
const version = app.node.tryGetContext("versionNumber")
const commit = app.node.tryGetContext("commitId")
// Retrieve new context values
const logRetentionInDays = app.node.tryGetContext("logRetentionInDays")
const logLevel = app.node.tryGetContext("logLevel")

Aspects.of(app).add(new AwsSolutionsChecks({verbose: true}))

Tags.of(app).add("cdkApp", "EpsAssistMe")
Tags.of(app).add("stackName", stackName ?? "unknown")
Tags.of(app).add("version", version ?? "dev")
Tags.of(app).add("commit", commit ?? "none")

new EpsAssistMeStack(app, "EpsAssistMeStack", {
  env: {
    region: "eu-west-2",
    account: accountId
  },
  stackName: stackName,
  version: version,
  commitId: commit,
  logRetentionInDays: parseInt(logRetentionInDays),
  logLevel: logLevel
})
