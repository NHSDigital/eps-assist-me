import {Construct} from "constructs"
import {Duration, CustomResource, RemovalPolicy} from "aws-cdk-lib"
import {
  Role,
  ServicePrincipal,
  PolicyStatement,
  ManagedPolicy
} from "aws-cdk-lib/aws-iam"
import {LogGroup, RetentionDays} from "aws-cdk-lib/aws-logs"
import {Provider} from "aws-cdk-lib/custom-resources"
import {Runtime, Function as LambdaFunction, Code} from "aws-cdk-lib/aws-lambda"
import {Key} from "aws-cdk-lib/aws-kms"

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
        "logs:PutLogEvents"
      ],
      resources: [modelInvocationLogGroup.logGroupArn]
    }))

    // Grant KMS permissions
    kmsKey.grantEncryptDecrypt(bedrockLoggingRole)

    // Create Lambda execution role for custom resource
    const lambdaRole = new Role(this, "LoggingConfigLambdaRole", {
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
      description: "Role for Lambda to configure Bedrock logging"
    })

    // Add basic Lambda execution permissions
    lambdaRole.addManagedPolicy(
      ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole")
    )

    // Grant permissions to configure Bedrock logging
    lambdaRole.addToPolicy(new PolicyStatement({
      actions: [
        "bedrock:PutModelInvocationLoggingConfiguration",
        "bedrock:GetModelInvocationLoggingConfiguration",
        "bedrock:DeleteModelInvocationLoggingConfiguration"
      ],
      resources: ["*"]
    }))

    // Grant permission to pass the Bedrock logging role
    lambdaRole.addToPolicy(new PolicyStatement({
      actions: ["iam:PassRole"],
      resources: [bedrockLoggingRole.roleArn]
    }))

    // Create Lambda function for custom resource
    const loggingConfigFunction = new LambdaFunction(this, "LoggingConfigFunction", {
      runtime: Runtime.PYTHON_3_14,
      handler: "handler.handler",
      code: Code.fromAsset("packages/bedrockLoggingConfigFunction/app"),
      timeout: Duration.minutes(5),
      role: lambdaRole,
      description: "Custom resource to configure Bedrock model invocation logging",
      environment: {
        ENABLE_LOGGING: props.enableLogging !== undefined ? props.enableLogging.toString() : "true"
      }
    })

    // Create custom resource provider
    const provider = new Provider(this, "LoggingConfigProvider", {
      onEventHandler: loggingConfigFunction
    })

    // Create custom resource
    new CustomResource(this, "BedrockLoggingConfig", {
      serviceToken: provider.serviceToken,
      properties: {
        CloudWatchLogGroupName: modelInvocationLogGroup.logGroupName,
        CloudWatchRoleArn: bedrockLoggingRole.roleArn,
        TextDataDeliveryEnabled: "true",
        ImageDataDeliveryEnabled: "true",
        EmbeddingDataDeliveryEnabled: "true"
      }
    })

    this.modelInvocationLogGroup = modelInvocationLogGroup
    this.bedrockLoggingRole = bedrockLoggingRole
  }
}
