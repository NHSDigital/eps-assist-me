#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib'
import {EpsAssistMeStack} from '../stacks/EpsAssistMeStack'

const app = new cdk.App()

/* Required Context:
  - stackName
  - version
  - commit
*/

const stackName = app.node.tryGetContext("stackName")
const version = app.node.tryGetContext("VERSION_NUMBER")
const commit = app.node.tryGetContext("COMMIT_ID")

new EpsAssistMeStack(app, 'EpsAssistMeStack', {
  env: {region: "eu-west-2"},
  stackName: stackName,
  version: version,
  commitId: commit
})
