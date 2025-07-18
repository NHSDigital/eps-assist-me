import {
  App,
  Stack,
  StackProps,
  RemovalPolicy,
  Fn,
  CfnOutput
} from "aws-cdk-lib"
import {
  Bucket,
  BucketEncryption,
  BlockPublicAccess,
  CfnBucket,
  CfnBucketPolicy
} from "aws-cdk-lib/aws-s3"
import {CfnFunction} from "aws-cdk-lib/aws-lambda"
import {Key} from "aws-cdk-lib/aws-kms"
import {PolicyStatement} from "aws-cdk-lib/aws-iam"
import {
  CfnGuardrail,
  CfnGuardrailVersion,
  CfnKnowledgeBase,
  CfnDataSource
} from "aws-cdk-lib/aws-bedrock"
import {RestApiGateway} from "../resources/RestApiGateway"
import {LambdaFunction} from "../resources/LambdaFunction"
import {LambdaIntegration} from "aws-cdk-lib/aws-apigateway"
import * as ops from "aws-cdk-lib/aws-opensearchserverless"
import * as cr from "aws-cdk-lib/custom-resources"
import {nagSuppressions} from "../nagSuppressions"

export interface EpsAssistMeStackProps extends StackProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
}

export class EpsAssistMeStack extends Stack {
  public constructor(scope: App, id: string, props: EpsAssistMeStackProps) {
    super(scope, id, props)

    // ==== Context and constants ====
    const region = Stack.of(this).region
    const account = Stack.of(this).account
    const logRetentionInDays = Number(this.node.tryGetContext("logRetentionInDays")) || 14
    const logLevel: string = this.node.tryGetContext("logLevel")
    const slackBotToken: string = this.node.tryGetContext("slackBotToken")
    const slackSigningSecret: string = this.node.tryGetContext("slackSigningSecret")

    // ==== KMS Key Import ====
    const cloudWatchLogsKmsKey = Key.fromKeyArn(
      this,
      "cloudWatchLogsKmsKey",
      Fn.importValue("account-resources:CloudwatchLogsKmsKeyArn")
    )

    // ==== Access Logs Bucket ====
    const accessLogBucket = new Bucket(this, "EpsAssistAccessLogsBucket", {
      encryption: BucketEncryption.KMS,
      encryptionKey: cloudWatchLogsKmsKey,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      versioned: true
    })

    // Add S3 replication and logging
    const accessLogBucketCfn = accessLogBucket.node.defaultChild as CfnBucket
    accessLogBucketCfn.replicationConfiguration = {
      role: `arn:aws:iam::${account}:role/account-resources-s3-replication-role`,
      rules: [{
        status: "Enabled",
        priority: 1,
        destination: {
          bucket: "arn:aws:s3:::dummy-replication-bucket"
        },
        deleteMarkerReplication: {status: "Disabled"}
      }]
    }
    accessLogBucketCfn.loggingConfiguration = {
      destinationBucketName: accessLogBucket.bucketName,
      logFilePrefix: "self-logs/"
    }

    new CfnBucketPolicy(this, "AccessLogsBucketStrictTLSOnly", {
      bucket: accessLogBucket.bucketName,
      policyDocument: {
        Version: "2012-10-17",
        Statement: [{
          Action: "s3:*",
          Effect: "Deny",
          Principal: "*",
          Resource: "*",
          Condition: {
            Bool: {"aws:SecureTransport": false}
          }
        }]
      }
    })

    // ==== Document Bucket ====
    const kbDocsBucket = new Bucket(this, "EpsAssistDocsBucket", {
      encryptionKey: cloudWatchLogsKmsKey,
      encryption: BucketEncryption.KMS,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      serverAccessLogsBucket: accessLogBucket,
      serverAccessLogsPrefix: "s3-access-logs/"
    })

    const kbDocsBucketCfn = kbDocsBucket.node.defaultChild as CfnBucket
    kbDocsBucketCfn.replicationConfiguration = {
      role: `arn:aws:iam::${account}:role/account-resources-s3-replication-role`,
      rules: [{
        status: "Enabled",
        priority: 1,
        destination: {
          bucket: "arn:aws:s3:::dummy-replication-bucket"
        },
        deleteMarkerReplication: {status: "Disabled"}
      }]
    }

    new CfnBucketPolicy(this, "KbDocsBucketStrictTLSOnly", {
      bucket: kbDocsBucket.bucketName,
      policyDocument: {
        Version: "2012-10-17",
        Statement: [{
          Action: "s3:*",
          Effect: "Deny",
          Principal: "*",
          Resource: "*",
          Condition: {
            Bool: {"aws:SecureTransport": false}
          }
        }]
      }
    })

    // ==== Guardrail ====
    const guardrail = new CfnGuardrail(this, "EpsGuardrail", {
      name: "eps-assist-guardrail",
      description: "Guardrail for EPS Assist Me bot",
      blockedInputMessaging: "Your input was blocked.",
      blockedOutputsMessaging: "Your output was blocked.",
      contentPolicyConfig: {
        filtersConfig: [
          {type: "SEXUAL", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "VIOLENCE", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "HATE", inputStrength: "HIGH", outputStrength: "HIGH"}
        ]
      },
      sensitiveInformationPolicyConfig: {
        piiEntitiesConfig: [
          {type: "EMAIL", action: "ANONYMIZE"},
          {type: "NAME", action: "ANONYMIZE"}
        ]
      },
      wordPolicyConfig: {
        managedWordListsConfig: [{type: "PROFANITY"}]
      }
    })

    const guardrailVersion = new CfnGuardrailVersion(this, "EpsGuardrailVersion", {
      guardrailIdentifier: guardrail.attrGuardrailId,
      description: "Initial version of the EPS Assist Me Guardrail"
    })

    // ==== OpenSearch Vector Store ====
    const osCollection = new ops.CfnCollection(this, "OsCollection", {
      name: "eps-assist-vector-db",
      description: "EPS Assist Vector Store",
      type: "VECTORSEARCH"
    })

    new ops.CfnSecurityPolicy(this, "OsEncryptionPolicy", {
      name: "eps-assist-encryption-policy",
      type: "encryption",
      policy: JSON.stringify({
        Rules: [{ResourceType: "collection", Resource: ["collection/eps-assist-vector-db"]}],
        AWSOwnedKey: true
      })
    })

    new ops.CfnSecurityPolicy(this, "OsNetworkPolicy", {
      name: "eps-assist-network-policy",
      type: "network",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: ["collection/eps-assist-vector-db"]},
          {ResourceType: "dashboard", Resource: ["collection/eps-assist-vector-db"]}
        ],
        AllowFromPublic: true
      }])
    })

    // ==== Lambda Function: CreateIndex ====
    const createIndexFunction = new LambdaFunction(this, "CreateIndexFunction", {
      stackName: props.stackName,
      functionName: `${props.stackName}-CreateIndexFunction`,
      packageBasePath: "packages/createIndexFunction",
      entryPoint: "app.py",
      logRetentionInDays,
      logLevel,
      environmentVariables: {"INDEX_NAME": osCollection.attrId},
      additionalPolicies: []
    })

    // Add cfn-guard suppressions for CreateIndex Lambda
    const createIndexLambdaCfn = createIndexFunction.function.node.defaultChild as CfnFunction
    createIndexLambdaCfn.cfnOptions.metadata = {
      guard: {
        SuppressedRules: [
          "LAMBDA_DLQ_CHECK",
          "LAMBDA_INSIDE_VPC",
          "LAMBDA_CONCURRENCY_CHECK"
        ]
      }
    }

    // ==== OpenSearch Access Policy ====
    new ops.CfnAccessPolicy(this, "OsAccessPolicy", {
      name: "eps-assist-access-policy",
      type: "data",
      policy: JSON.stringify([{
        Rules: [
          {ResourceType: "collection", Resource: ["collection/*"], Permission: ["aoss:*"]},
          {ResourceType: "index", Resource: ["index/*/*"], Permission: ["aoss:*"]}
        ],
        Principal: [
          `arn:aws:iam::${account}:role/${createIndexFunction.function.role?.roleName}`,
          `arn:aws:iam::${account}:root`
        ]
      }])
    })

    // ==== Trigger Vector Index Creation ====
    const endpoint = `${osCollection.attrId}.${region}.aoss.amazonaws.com`
    new cr.AwsCustomResource(this, "VectorIndex", {
      installLatestAwsSdk: true,
      onCreate: {
        service: "Lambda",
        action: "invoke",
        parameters: {
          FunctionName: createIndexFunction.function.functionName,
          InvocationType: "RequestResponse",
          Payload: JSON.stringify({
            RequestType: "Create",
            CollectionName: osCollection.name,
            IndexName: "eps-assist-os-index",
            Endpoint: endpoint
          })
        },
        physicalResourceId: cr.PhysicalResourceId.of("VectorIndex")
      },
      onDelete: {
        service: "Lambda",
        action: "invoke",
        parameters: {
          FunctionName: createIndexFunction.function.functionName,
          InvocationType: "RequestResponse",
          Payload: JSON.stringify({
            RequestType: "Delete",
            CollectionName: osCollection.name,
            IndexName: "eps-assist-os-index",
            Endpoint: endpoint
          })
        }
      },
      policy: cr.AwsCustomResourcePolicy.fromStatements([
        new PolicyStatement({
          actions: ["lambda:InvokeFunction"],
          resources: [createIndexFunction.function.functionArn]
        })
      ])
    })

    // ==== Bedrock Knowledge Base ====
    const kb = new CfnKnowledgeBase(this, "EpsKb", {
      name: "eps-assist-kb",
      description: "EPS Assist Knowledge Base",
      roleArn: Fn.importValue("account-resources:BedrockExecutionRoleArn"),
      knowledgeBaseConfiguration: {
        type: "VECTOR",
        vectorKnowledgeBaseConfiguration: {
          embeddingModelArn: `arn:aws:bedrock:${region}::foundation-model/amazon.titan-embed-text-v2:0`
        }
      },
      storageConfiguration: {
        type: "OPENSEARCH_SERVERLESS",
        opensearchServerlessConfiguration: {
          collectionArn: osCollection.attrArn,
          vectorIndexName: "eps-assist-os-index",
          fieldMapping: {
            vectorField: "bedrock-knowledge-base-default-vector",
            textField: "AMAZON_BEDROCK_TEXT_CHUNK",
            metadataField: "AMAZON_BEDROCK_METADATA"
          }
        }
      }
    })

    new CfnDataSource(this, "EpsKbDataSource", {
      name: "eps-assist-kb-ds",
      knowledgeBaseId: kb.attrKnowledgeBaseId,
      dataSourceConfiguration: {
        type: "S3",
        s3Configuration: {
          bucketArn: kbDocsBucket.bucketArn
        }
      }
    })

    // ==== SlackBot Lambda ====
    const lambdaEnv: {[key: string]: string} = {
      RAG_MODEL_ID: "anthropic.claude-3-sonnet-20240229-v1:0",
      EMBEDDING_MODEL: "amazon.titan-embed-text-v2:0",
      SLACK_SLASH_COMMAND: "/ask-eps",
      COLLECTION_NAME: "eps-assist-vector-db",
      VECTOR_INDEX_NAME: "eps-assist-os-index",
      BEDROCK_KB_NAME: "eps-assist-kb",
      BEDROCK_KB_DATA_SOURCE: "eps-assist-kb-ds",
      LAMBDA_MEMORY_SIZE: "265",
      KNOWLEDGEBASE_ID: kb.attrKnowledgeBaseId,
      GUARD_RAIL_ID: guardrail.attrGuardrailId,
      GUARD_RAIL_VERSION: guardrailVersion.attrVersion,
      SLACK_BOT_TOKEN: slackBotToken,
      SLACK_SIGNING_SECRET: slackSigningSecret
    }

    const slackBotLambda = new LambdaFunction(this, "SlackBotLambda", {
      stackName: props.stackName,
      functionName: `${props.stackName}-SlackBotFunction`,
      packageBasePath: "packages/slackBotFunction",
      entryPoint: "app.py",
      logRetentionInDays,
      logLevel,
      environmentVariables: lambdaEnv,
      additionalPolicies: []
    })

    const slackBotLambdaCfn = slackBotLambda.function.node.defaultChild as CfnFunction
    slackBotLambdaCfn.cfnOptions.metadata = {
      guard: {
        SuppressedRules: [
          "LAMBDA_DLQ_CHECK",
          "LAMBDA_INSIDE_VPC",
          "LAMBDA_CONCURRENCY_CHECK"
        ]
      }
    }

    // AwsCustomResource internal Lambda handler suppression
    const customResourceHandler = this.node
      .tryFindChild("VectorIndex")
      ?.node.tryFindChild("CustomResourceProvider")
      ?.node.tryFindChild("Handler")
    const customResourceHandlerCfn = customResourceHandler?.node.defaultChild as CfnFunction
    if (customResourceHandlerCfn) {
      customResourceHandlerCfn.cfnOptions.metadata = {
        guard: {
          SuppressedRules: [
            "LAMBDA_DLQ_CHECK",
            "LAMBDA_INSIDE_VPC"
          ]
        }
      }
    }

    // ==== API Gateway + Slack Route ====
    const apiGateway = new RestApiGateway(this, "EpsAssistApiGateway", {
      stackName: props.stackName,
      logRetentionInDays,
      enableMutualTls: false,
      trustStoreKey: "unused",
      truststoreVersion: "unused"
    })

    const slackRoute = apiGateway.api.root.addResource("slack").addResource("ask-eps")
    slackRoute.addMethod("POST", new LambdaIntegration(slackBotLambda.function, {
      credentialsRole: apiGateway.role
    }))

    apiGateway.role.addManagedPolicy(slackBotLambda.executionPolicy)

    new CfnOutput(this, "SlackBotEndpoint", {
      value: `https://${apiGateway.api.domainName?.domainName}/slack/ask-eps`
    })

    // ==== Suppressions for CDK-generated Lambda handlers ====
    // Suppress CDK-generated S3 AutoDeleteObjects handler
    const customS3Handler = Stack.of(this).node
      .tryFindChild("Custom::S3AutoDeleteObjectsCustomResourceProvider")
      ?.node.tryFindChild("Handler")

    const customS3HandlerCfn = customS3Handler?.node.defaultChild as CfnFunction

    if (customS3HandlerCfn) {
      customS3HandlerCfn.cfnOptions.metadata = {
        guard: {
          SuppressedRules: [
            "LAMBDA_DLQ_CHECK",
            "LAMBDA_INSIDE_VPC"
          ]
        }
      }
    }

    // Suppress AWS679f... CDK-generated unnamed Lambda (e.g., AwsCustomResource)
    for (const construct of this.node.findAll()) {
      const fn = construct.node.defaultChild
      if (
        fn instanceof CfnFunction &&
        fn.logicalId.startsWith("AWS679f")
      ) {
        fn.cfnOptions.metadata = {
          guard: {
            SuppressedRules: [
              "LAMBDA_DLQ_CHECK",
              "LAMBDA_INSIDE_VPC"
            ]
          }
        }
      }
    }

    // ==== Final CDK Nag Suppressions ====
    nagSuppressions(this)
  }
}
