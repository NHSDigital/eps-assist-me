#!/usr/bin/env node
import {App, Aspects, Tags} from "aws-cdk-lib"
import {AwsSolutionsChecks} from "cdk-nag"
import {EpsAssistMeStack} from "../stacks/EpsAssistMeStack"
import {applyCfnGuardSuppressions} from "./utils/appUtils"

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
const cfnDriftDetectionGroup = app.node.tryGetContext("cfnDriftDetectionGroup")

Aspects.of(app).add(new AwsSolutionsChecks({verbose: true}))

Tags.of(app).add("cdkApp", "EpsAssistMe")
Tags.of(app).add("accountId", accountId)
Tags.of(app).add("stackName", stackName)
Tags.of(app).add("version", version)
Tags.of(app).add("commit", commit)
Tags.of(app).add("cfnDriftDetectionGroup", cfnDriftDetectionGroup)

const EpsAssistMe = new EpsAssistMeStack(app, "EpsAssistMeStack", {
  env: {
    region: "eu-west-2",
    account: accountId
  },
  stackName: stackName,
  version: version,
  commitId: commit
})

applyCfnGuardSuppressions(EpsAssistMe)

app.synth()
