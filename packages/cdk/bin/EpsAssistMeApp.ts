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

console.log("CDK context:", {accountId, stackName, version, commit})

Aspects.of(app).add(new AwsSolutionsChecks({verbose: true}))

Tags.of(app).add("cdkApp", "EpsAssistMe")
Tags.of(app).add("accountId", accountId)
Tags.of(app).add("stackName", stackName)
Tags.of(app).add("version", version)
Tags.of(app).add("commit", commit)

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
addCfnGuardMetadata(EpsAssistMe, "AWS679f53fac002430cb0da5b7982bd2287", "Resource",
  ["LAMBDA_DLQ_CHECK", "LAMBDA_INSIDE_VPC"]
)
addCfnGuardMetadata(EpsAssistMe, "CustomS3AutoDeleteObjectsCustomResourceProviderHandler9D90184F", "Resource",
  ["LAMBDA_DLQ_CHECK", "LAMBDA_INSIDE_VPC"]
)
addCfnGuardMetadata(EpsAssistMe, "EpsAssistAccessLogsBucket", "Resource",
  ["S3_BUCKET_LOGGING_ENABLED", "S3_BUCKET_SSL_REQUESTS_ONLY"]
)

// Suppress Lambda DLQ and VPC checks for application Lambda functions
addCfnGuardMetadata(EpsAssistMe, "FunctionsCreateIndexFunctionepsam-CreateIndexFunction", "Resource",
  ["LAMBDA_DLQ_CHECK", "LAMBDA_INSIDE_VPC"]
)
addCfnGuardMetadata(EpsAssistMe, "FunctionsSlackBotLambdaepsam-SlackBotFunction", "Resource",
  ["LAMBDA_DLQ_CHECK", "LAMBDA_INSIDE_VPC"]
)

// Suppress cfn-guard rules for S3 buckets (SSL is enforced by CDK, replication not needed for this use case)
addCfnGuardMetadata(EpsAssistMe, "StorageAccessLogsBucketAccessLogs86FA3BBC", "Resource",
  ["S3_BUCKET_REPLICATION_ENABLED", "S3_BUCKET_LOGGING_ENABLED", "S3_BUCKET_VERSIONING_ENABLED"]
)
addCfnGuardMetadata(EpsAssistMe, "StorageDocsBucketDocs0C9A9D9E", "Resource",
  ["S3_BUCKET_REPLICATION_ENABLED"]
)

// Suppress SSL policy format differences (CDK enforceSSL creates equivalent but different format)
addCfnGuardMetadata(EpsAssistMe, "StorageAccessLogsBucketAccessLogsPolicy523966CD", "Resource",
  ["S3_BUCKET_SSL_REQUESTS_ONLY"]
)
addCfnGuardMetadata(EpsAssistMe, "StorageDocsBucketDocsPolicy8F1C9E94", "Resource",
  ["S3_BUCKET_SSL_REQUESTS_ONLY"]
)

// Finally run synth again with force to include the added metadata
app.synth({
  force: true
})
