#!/usr/bin/env bash

mkdir -p .dependencies/slackBotFunction
mkdir -p .dependencies/syncKnowledgeBaseFunction
mkdir -p .dependencies/preprocessingFunction
mkdir -p .dependencies/bedrockLoggingConfigFunction
mkdir -p .local_config

# this is needed and wont change
CDK_APP_NAME=EpsAssistMeApp
CDK_STACK_NAME="EpsAssistMeBasepathMapping"

# these are just dummy values and are not used
# but they are needed for cdk to synth correctly
CDK_CONFIG_isPullRequest=false
CDK_CONFIG_domainName=epsam
CDK_CONFIG_enableBedrockLogging=false
CDK_CONFIG_runRegressionTests=true
CDK_CONFIG_forwardCsocLogs=true
CDK_CONFIG_slackBotToken=foo
CDK_CONFIG_slackSigningSecret=bar
CDK_CONFIG_logRetentionInDays=30
CDK_CONFIG_logLevel=DEBUG

# these should be set to show rollback happened
CDK_CONFIG_versionNumber=change_me
CDK_CONFIG_commitId=change_me

# change these to match the environment
CDK_CONFIG_environment=dev

# this is the name of the bpm stack that we are going to deploy an updated version
CDK_CONFIG_stackName=epsam-pr-336

# this is the name of the stateful stack - should not change
CDK_CONFIG_statefulStackName=epsam-pr-336-stateful

# this is the name of the stateless stack we want to switch to
CDK_CONFIG_statelessStackName=epsam-pr-336-stateless-new

# export all variables so they are available to npm script
export CDK_APP_NAME
export CDK_CONFIG_stackName
export CDK_CONFIG_isPullRequest
export CDK_CONFIG_domainName
export CDK_CONFIG_enableBedrockLogging
export CDK_CONFIG_runRegressionTests
export CDK_CONFIG_forwardCsocLogs
export CDK_CONFIG_slackBotToken
export CDK_CONFIG_slackSigningSecret
export CDK_CONFIG_statefulStackName
export CDK_CONFIG_statelessStackName
export CDK_STACK_NAME
export CDK_CONFIG_versionNumber
export CDK_CONFIG_commitId
export CDK_CONFIG_logRetentionInDays
export CDK_CONFIG_logLevel
export CDK_CONFIG_environment

# now deploy
npm run cdk-deploy --workspace packages/cdk/
