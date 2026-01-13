import {Construct} from "constructs"
import {CustomResource, RemovalPolicy} from "aws-cdk-lib"
import {
  Role,
  ServicePrincipal,
  PolicyStatement,
  ManagedPolicy
} from "aws-cdk-lib/aws-iam"
import {LogGroup, RetentionDays} from "aws-cdk-lib/aws-logs"
import {Provider} from "aws-cdk-lib/custom-resources"
import {Key} from "aws-cdk-lib/aws-kms"
import {LambdaFunction} from "../constructs/LambdaFunction"

export interface BedrockLoggingConfigurationProps {
  readonly stackName: string
  readonly region: string
  readonly account: string
  readonly logRetentionInDays: number
  readonly enableLogging?: boolean
}

export class BedrockLoggingConfiguration extends Construct {
  public readonly modelInvocationLogGroup: LogGroup
  public readonly bedrockLoggingRole: Role

  constructor(scope: Construct, id: string, props: BedrockLoggingConfigurationProps) {
    super(scope, id)

    // Create KMS key for encryption
    const kmsKey = new Key(this, "BedrockLogsKmsKey", {
      description: `KMS key for ${props.stackName} Bedrock logs encryption`,
      enableKeyRotation: true,
      removalPolicy: RemovalPolicy.DESTROY
    })

    // Create CloudWatch Log Group for model invocations
    const modelInvocationLogGroup = new LogGroup(this, "ModelInvocationLogGroup", {
      logGroupName: `/aws/bedrock/${props.stackName}/model-invocations`,
      retention: props.logRetentionInDays as RetentionDays,
      encryptionKey: kmsKey,
      removalPolicy: RemovalPolicy.DESTROY
    })

    // Grant CloudWatch Logs service permission to use KMS key
    kmsKey.addToResourcePolicy(new PolicyStatement({
      sid: "Allow CloudWatch Logs",
      principals: [new ServicePrincipal(`logs.${props.region}.amazonaws.com`)],
      actions: [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:ReEncrypt*",
        "kms:GenerateDataKey*",
        "kms:CreateGrant",
        "kms:DescribeKey"
      ],
      resources: ["*"],
      conditions: {
        ArnLike: {
          "kms:EncryptionContext:aws:logs:arn":
          `arn:aws:logs:${props.region}:${props.account}:log-group:/aws/bedrock/${props.stackName}/*`
        }
      }
    }))

    // Create IAM role for Bedrock to write logs
    const bedrockLoggingRole = new Role(this, "BedrockLoggingRole", {
      assumedBy: new ServicePrincipal("bedrock.amazonaws.com"),
      description: "Role for Bedrock to write model invocation logs"
    })

    // Grant permissions to write to CloudWatch Logs
    bedrockLoggingRole.addToPolicy(new PolicyStatement({
      actions: [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      resources: [
        modelInvocationLogGroup.logGroupArn,
        `${modelInvocationLogGroup.logGroupArn}:*`
      ]
    }))

    // Grant KMS permissions
    kmsKey.grantEncryptDecrypt(bedrockLoggingRole)

    // Create managed policy for Bedrock logging configuration
    const bedrockLoggingConfigPolicy = new ManagedPolicy(this, "BedrockLoggingConfigPolicy", {
      description: "Policy for Lambda to configure Bedrock logging",
      statements: [
        new PolicyStatement({
          actions: [
            "bedrock:PutModelInvocationLoggingConfiguration",
            "bedrock:GetModelInvocationLoggingConfiguration",
            "bedrock:DeleteModelInvocationLoggingConfiguration"
          ],
          resources: ["*"]
        }),
        new PolicyStatement({
          actions: ["iam:PassRole"],
          resources: [bedrockLoggingRole.roleArn]
        })
      ]
    })

    // Create Lambda function for custom resource
    const loggingConfigFunction = new LambdaFunction(this, "LoggingConfigFunction", {
      stackName: props.stackName,
      functionName: `${props.stackName}-BedrockLoggingConfig`,
      packageBasePath: "packages/bedrockLoggingConfigFunction",
      handler: "app.handler.handler",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: "INFO",
      additionalPolicies: [bedrockLoggingConfigPolicy],
      dependencyLocation: ".dependencies/bedrockLoggingConfigFunction",
      environmentVariables: {
        ENABLE_LOGGING: props.enableLogging !== undefined ? props.enableLogging.toString() : "true",
        CLOUDWATCH_LOG_GROUP_NAME: modelInvocationLogGroup.logGroupName,
        CLOUDWATCH_ROLE_ARN: bedrockLoggingRole.roleArn
      }
    })

    // Create custom resource provider
    const provider = new Provider(this, "LoggingConfigProvider", {
      onEventHandler: loggingConfigFunction.function
    })

    // Create custom resource
    new CustomResource(this, "BedrockLoggingConfig", {
      serviceToken: provider.serviceToken,
      properties: {
        TextDataDeliveryEnabled: "true",
        ImageDataDeliveryEnabled: "true",
        EmbeddingDataDeliveryEnabled: "true"
      }
    })

    this.modelInvocationLogGroup = modelInvocationLogGroup
    this.bedrockLoggingRole = bedrockLoggingRole
  }
}
