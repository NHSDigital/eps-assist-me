#!/usr/bin/env node
import {App, Aspects, Tags} from "aws-cdk-lib"
import {AwsSolutionsChecks} from "cdk-nag"
import {EpsAssistMeStack} from "../stacks/EpsAssistMeStack"
import {applyCfnGuardSuppressions} from "./utils/appUtils"
import fs from "fs"

// read the config in
const configFileName = process.env["CONFIG_FILE_NAME"]
if (configFileName === undefined) {
  throw new Error("Can not read config file")
}

const configDetails = JSON.parse(fs.readFileSync(configFileName, "utf-8"))

// create the app using the config details
const app = new App({context: configDetails})

/* Required Context:
- accountId
- stackName
- version
- commit
*/

const stackName = app.node.tryGetContext("stackName")
const version = app.node.tryGetContext("versionNumber")
const commit = app.node.tryGetContext("commitId")
const cfnDriftDetectionGroup = app.node.tryGetContext("cfnDriftDetectionGroup")

Aspects.of(app).add(new AwsSolutionsChecks({verbose: true}))

Tags.of(app).add("cdkApp", "EpsAssistMe")
Tags.of(app).add("stackName", stackName)
Tags.of(app).add("version", version)
Tags.of(app).add("commit", commit)
Tags.of(app).add("cfnDriftDetectionGroup", cfnDriftDetectionGroup)

const EpsAssistMe = new EpsAssistMeStack(app, "EpsAssistMeStack", {
  env: {
    region: "eu-west-2",
    account: process.env.CDK_DEFAULT_ACCOUNT || undefined
  },
  stackName: stackName,
  version: version,
  commitId: commit
})

applyCfnGuardSuppressions(EpsAssistMe)

app.synth()
