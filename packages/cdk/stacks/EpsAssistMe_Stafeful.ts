import {
  App,
  Stack,
  StackProps,
  CfnOutput,
  Fn
} from "aws-cdk-lib"
import {nagSuppressions} from "../nagSuppressions"
import {StatefulFunctions} from "../resources/StatefulFunctions"
import {Storage} from "../resources/Storage"
import {OpenSearchResources} from "../resources/OpenSearchResources"
import {VectorKnowledgeBaseResources} from "../resources/VectorKnowledgeBaseResources"
import {BedrockExecutionRole} from "../resources/BedrockExecutionRole"
import {StatefulRuntimePolicies} from "../resources/StatefulRuntimePolicies"
import {DatabaseTables} from "../resources/DatabaseTables"
import {S3LambdaNotification} from "../constructs/S3LambdaNotification"
import {VectorIndex} from "../resources/VectorIndex"
import {BucketDeployment, Source} from "aws-cdk-lib/aws-s3-deployment"
import {BedrockLoggingConfiguration} from "../resources/BedrockLoggingConfiguration"
import {Bucket} from "aws-cdk-lib/aws-s3"
import {ApiDomainName} from "../resources/DomainName"
import {Role} from "aws-cdk-lib/aws-iam"

export interface EpsAssistMe_StatefulProps extends StackProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
}

export class EpsAssistMe_Stateful extends Stack {
  public constructor(scope: App, id: string, props: EpsAssistMe_StatefulProps) {
    super(scope, id, props)

    // imports
    const deploymentRoleImport = Fn.importValue("ci-resources:CloudFormationDeployRole")
    // regression testing needs direct lambda invoke — bypasses slack webhooks entirely
    const auditLoggingBucketImport = Fn.importValue("account-resources:AuditLoggingBucket")

    // Get variables from context
    const region = Stack.of(this).region
    const account = Stack.of(this).account
    const cdkExecRoleArn = `arn:aws:iam::${account}:role/cdk-hnb659fds-cfn-exec-role-${account}-${region}`

    const logRetentionInDays = Number(this.node.tryGetContext("logRetentionInDays"))
    const logLevel: string = this.node.tryGetContext("logLevel")
    const isPullRequest: boolean = this.node.tryGetContext("isPullRequest")
    const enableBedrockLogging: boolean = this.node.tryGetContext("enableBedrockLogging") === "true"

    // Get secrets from context or fail if not provided
    const slackBotToken: string = this.node.tryGetContext("slackBotToken")
    const slackSigningSecret: string = this.node.tryGetContext("slackSigningSecret")

    const cdkExecRole = Role.fromRoleArn(this, "CdkExecRole", cdkExecRoleArn)
    const deploymentRole = Role.fromRoleArn(this, "deploymentRole", deploymentRoleImport)
    const auditLoggingBucket = Bucket.fromBucketArn(
      this, "AuditLoggingBucket", auditLoggingBucketImport)

    if (!slackBotToken || !slackSigningSecret) {
      throw new Error("Missing required context variables. Please provide slackBotToken and slackSigningSecret")
    }

    // Create DatabaseTables
    const tables = new DatabaseTables(this, "DatabaseTables", {
      stackName: props.stackName
    })

    // Create Storage construct first as it has no dependencies
    const storage = new Storage(this, "Storage", {
      stackName: props.stackName,
      deploymentRole: deploymentRole,
      auditLoggingBucket: auditLoggingBucket
    })

    // initialize s3 folders for raw and processed documents
    new BucketDeployment(this, "S3FolderInitializer", {
      sources: [Source.asset("packages/cdk/assets/s3-folders")],
      destinationBucket: storage.kbDocsBucket
    })

    // Create Bedrock execution role without dependencies
    const bedrockExecutionRole = new BedrockExecutionRole(this, "BedrockExecutionRole", {
      region,
      account,
      kbDocsBucket: storage.kbDocsBucket,
      kbDocsKmsKey: storage.kbDocsKmsKey
    })

    // Create OpenSearch Resources with Bedrock execution role
    const openSearchResources = new OpenSearchResources(this, "OpenSearchResources", {
      stackName: props.stackName,
      bedrockExecutionRole: bedrockExecutionRole.role,
      cdkExecutionRole: cdkExecRole,
      region
    })

    const vectorIndex = new VectorIndex(this, "VectorIndex", {
      stackName: props.stackName,
      collection: openSearchResources.collection
    })

    // This dependency ensures the OpenSearch access policy is created before the VectorIndex
    // and deleted after the VectorIndex is deleted to prevent deletion or deployment failures
    vectorIndex.node.addDependency(openSearchResources.deploymentPolicy)

    // Create Bedrock logging configuration for model invocations
    const bedrockLogging = new BedrockLoggingConfiguration(this, "BedrockLogging", {
      stackName: props.stackName,
      region,
      account,
      logRetentionInDays,
      enableLogging: enableBedrockLogging
    })

    // Create VectorKnowledgeBase construct with Bedrock execution role
    const vectorKB = new VectorKnowledgeBaseResources(this, "VectorKB", {
      stackName: props.stackName,
      docsBucket: storage.kbDocsBucket,
      bedrockExecutionRole: bedrockExecutionRole.role,
      collectionArn: openSearchResources.collection.collectionArn,
      vectorIndexName: vectorIndex.indexName,
      region,
      account,
      logRetentionInDays
    })

    vectorKB.knowledgeBase.node.addDependency(vectorIndex.indexReadyWait.customResource)
    // Create runtime policies with resource dependencies
    const runtimePolicies = new StatefulRuntimePolicies(this, "StatefulRuntimePolicies", {
      knowledgeBaseArn: vectorKB.knowledgeBase.attrKnowledgeBaseArn,
      dataSourceArn: vectorKB.dataSourceArn,
      docsBucketArn: storage.kbDocsBucket.bucketArn,
      docsBucketKmsKeyArn: storage.kbDocsKmsKey.keyArn
    })

    // Create Functions construct with actual values from VectorKB
    const functions = new StatefulFunctions(this, "StatefulFunctions", {
      stackName: props.stackName,
      version: props.version,
      commitId: props.commitId,
      logRetentionInDays,
      logLevel,
      syncKnowledgeBaseManagedPolicy: runtimePolicies.syncKnowledgeBasePolicy,
      preprocessingManagedPolicy: runtimePolicies.preprocessingPolicy,
      knowledgeBaseId: vectorKB.knowledgeBase.attrKnowledgeBaseId,
      dataSourceId: vectorKB.dataSource.attrDataSourceId,
      region,
      account,
      docsBucketName: storage.kbDocsBucket.bucketName
    })

    // Grant preprocessing Lambda access to the KMS key for S3 bucket
    storage.kbDocsKmsKey.grantEncryptDecrypt(functions.preprocessingFunction.executionRole)

    //S3 notification for raw/ prefix to trigger preprocessing Lambda
    new S3LambdaNotification(this, "S3RawNotification", {
      bucket: storage.kbDocsBucket,
      lambdaFunction: functions.preprocessingFunction.function,
      prefix: "raw/"
    })

    // S3 notification for processed/ prefix to trigger sync Lambda function
    new S3LambdaNotification(this, "S3ProcessedNotification", {
      bucket: storage.kbDocsBucket,
      lambdaFunction: functions.syncKnowledgeBaseFunction.function,
      prefix: "processed/"
    })

    const domainName = new ApiDomainName(this, "ApiDomainName", {
      stackName: props.stackName
    })

    // Output: SlackBot Endpoint
    new CfnOutput(this, "SlackBotEventsEndpoint", {
      value: `https://${domainName.domain.domainName}/slack/events`,
      description: "Slack Events API endpoint for @mentions and direct messages"
    })

    new CfnOutput(this, "kbDocsBucketArn", {
      value: storage.kbDocsBucket.bucketArn,
      exportName: `${props.stackName}:kbDocsBucket:Arn`
    })
    new CfnOutput(this, "kbDocsBucketName", {
      value: storage.kbDocsBucket.bucketName,
      exportName: `${props.stackName}:kbDocsBucket:Name`
    })

    new CfnOutput(this, "ModelInvocationLogGroupName", {
      value: bedrockLogging.modelInvocationLogGroup.logGroupName,
      description: "CloudWatch Log Group for Bedrock model invocations"
    })

    new CfnOutput(this, "KnowledgeBaseLogGroupName", {
      value: vectorKB.kbLogGroup.logGroupName,
      description: "CloudWatch Log Group for Knowledge Base application logs"
    })

    if (isPullRequest) {
      new CfnOutput(this, "VERSION_NUMBER", {
        value: props.version,
        exportName: `${props.stackName}:local:VERSION-NUMBER`
      })
      new CfnOutput(this, "COMMIT_ID", {
        value: props.commitId,
        exportName: `${props.stackName}:local:COMMIT-ID`
      })
      new CfnOutput(this, "slackBotToken", {
        value: slackBotToken,
        exportName: `${props.stackName}:local:slackBotToken`
      })
      new CfnOutput(this, "slackSigningSecret", {
        value: slackSigningSecret,
        exportName: `${props.stackName}:local:slackSigningSecret`
      })
    }

    new CfnOutput(this, "slackBotStateTableArn", {
      value: tables.slackBotStateTable.table.tableArn,
      exportName: `${props.stackName}:slackBotStateTable:Arn`
    })
    new CfnOutput(this, "slackBotStateTableName", {
      value: tables.slackBotStateTable.table.tableName,
      exportName: `${props.stackName}:slackBotStateTable:Name`
    })
    new CfnOutput(this, "slackBotStateTableKmsKeyArn", {
      value: tables.slackBotStateTable.kmsKey.keyArn,
      exportName: `${props.stackName}:slackBotStateTable:kmsKey:Arn`
    })
    new CfnOutput(this, "knowledgeBaseArn", {
      value: vectorKB.knowledgeBase.attrKnowledgeBaseArn,
      exportName: `${props.stackName}:knowledgeBase:Arn`
    })
    new CfnOutput(this, "knowledgeBaseId", {
      value: vectorKB.knowledgeBase.attrKnowledgeBaseId,
      exportName: `${props.stackName}:knowledgeBase:Id`
    })
    new CfnOutput(this, "dataSourceId", {
      value: vectorKB.dataSource.attrDataSourceId,
      exportName: `${props.stackName}:knowledgeBase:DataSourceId`
    })

    // Final CDK Nag Suppressions
    nagSuppressions(this, account)
  }
}
