#!/usr/bin/env node
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

// S3 Bucket: StorageAccessLogsBucketAccessLogs86FA3BBC
// CDK-Path: EpsAssistMeStack/Storage/AccessLogsBucket/AccessLogs/Resource
addCfnGuardMetadata(EpsAssistMe, "Storage/AccessLogsBucket", "AccessLogs",
  ["S3_BUCKET_REPLICATION_ENABLED", "S3_BUCKET_VERSIONING_ENABLED", "S3_BUCKET_LOGGING_ENABLED"]
)

// S3 Bucket Policy: StorageAccessLogsBucketAccessLogsPolicy523966CD
// CDK-Path: EpsAssistMeStack/Storage/AccessLogsBucket/AccessLogs/Policy/Resource
addCfnGuardMetadata(EpsAssistMe, "Storage/AccessLogsBucket/AccessLogs", "Policy",
  ["S3_BUCKET_SSL_REQUESTS_ONLY"]
)

// S3 Bucket: StorageDocsBucketDocs0C9A9D9E
// CDK-Path: EpsAssistMeStack/Storage/DocsBucket/Docs/Resource
addCfnGuardMetadata(EpsAssistMe, "Storage/DocsBucket", "Docs",
  ["S3_BUCKET_REPLICATION_ENABLED"]
)

// S3 Bucket Policy: StorageDocsBucketDocsPolicy8F1C9E94
// CDK-Path: EpsAssistMeStack/Storage/DocsBucket/Docs/Policy/Resource
addCfnGuardMetadata(EpsAssistMe, "Storage/DocsBucket/Docs", "Policy",
  ["S3_BUCKET_SSL_REQUESTS_ONLY"]
)

// S3 Bucket: StorageLoggingBucketLogging36F28A73
// CDK-Path: EpsAssistMeStack/Storage/LoggingBucket/Logging/Resource
addCfnGuardMetadata(EpsAssistMe, "Storage/LoggingBucket", "Logging",
  ["S3_BUCKET_REPLICATION_ENABLED", "S3_BUCKET_LOGGING_ENABLED"]
)

// S3 Bucket Policy: StorageLoggingBucketLoggingPolicy06AD29F1
// CDK-Path: EpsAssistMeStack/Storage/LoggingBucket/Logging/Policy/Resource
addCfnGuardMetadata(EpsAssistMe, "Storage/LoggingBucket/Logging", "Policy",
  ["S3_BUCKET_SSL_REQUESTS_ONLY"]
)

// Lambda Function: CustomS3AutoDeleteObjectsCustomResourceProviderHandler9D90184F
// CDK-Path: EpsAssistMeStack/Custom::S3AutoDeleteObjectsCustomResourceProvider/Handler
addCfnGuardMetadata(EpsAssistMe, "Custom::S3AutoDeleteObjectsCustomResourceProvider", "Handler",
  ["LAMBDA_DLQ_CHECK", "LAMBDA_INSIDE_VPC"]
)

// Suppress Lambda DLQ and VPC checks for application Lambda functions
addCfnGuardMetadata(EpsAssistMe, "FunctionsCreateIndexFunctionepsam-CreateIndexFunction", "Resource",
  ["LAMBDA_DLQ_CHECK", "LAMBDA_INSIDE_VPC"]
)
addCfnGuardMetadata(EpsAssistMe, "FunctionsSlackBotLambdaepsam-SlackBotFunction", "Resource",
  ["LAMBDA_DLQ_CHECK", "LAMBDA_INSIDE_VPC"]
)

// Finally run synth again with force to include the added metadata
app.synth({
  force: true
})
