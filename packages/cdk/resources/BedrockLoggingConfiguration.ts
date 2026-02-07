import {Construct} from "constructs"
import {CustomResource, Fn, RemovalPolicy} from "aws-cdk-lib"
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
import {NagSuppressions} from "cdk-nag"

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

    const cloudWatchLogsKmsKey = Key.fromKeyArn(
      scope, "cloudWatchLogsKmsKey", Fn.importValue("account-resources:CloudwatchLogsKmsKeyArn"))

    const cloudwatchEncryptionKMSPolicy = ManagedPolicy.fromManagedPolicyArn(
      scope, "cloudwatchEncryptionKMSPolicyArn", Fn.importValue("account-resources:CloudwatchEncryptionKMSPolicyArn"))

    // Create CloudWatch Log Group for model invocations
    const modelInvocationLogGroup = new LogGroup(this, "ModelInvocationLogGroup", {
      logGroupName: `/aws/bedrock/${props.stackName}/model-invocations`,
      retention: props.logRetentionInDays as RetentionDays,
      encryptionKey: cloudWatchLogsKmsKey,
      removalPolicy: RemovalPolicy.DESTROY
    })

    // Create IAM role for Bedrock to write logs
    const putLogsManagedPolicy = new ManagedPolicy(scope, "LambdaPutLogsManagedPolicy", {
      description: `write to ${modelInvocationLogGroup.logGroupName} logs`,
      statements: [
        new PolicyStatement({
          actions: [
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ],
          resources: [`${modelInvocationLogGroup.logGroupArn}:*` ]
        })
      ]
    })
    NagSuppressions.addResourceSuppressions(putLogsManagedPolicy, [
      {
        id: "AwsSolutions-IAM5",
        // eslint-disable-next-line max-len
        reason: "Suppress error for not having wildcards in permissions. This is a fine as we need to have permissions on all log streams under path"
      }
    ])

    const bedrockLoggingRole = new Role(this, "BedrockLoggingRole", {
      assumedBy: new ServicePrincipal("bedrock.amazonaws.com"),
      description: "Role for Bedrock to write model invocation logs",
      managedPolicies: [
        putLogsManagedPolicy,
        cloudwatchEncryptionKMSPolicy
      ]
    })

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
      },
      stackName: props.stackName
    })

    const frameworkInvokeBedrockLoggingPolicy = new ManagedPolicy(this,
      `${props.stackName}BedrockLoggingInvokeDelayFunctionPolicy`, {
        description: `Allow provider framework to invoke ${props.stackName} bedrock logging function`,
        statements: [
          new PolicyStatement({
            actions: [
              "lambda:InvokeFunction",
              "lambda:GetFunction"
            ],
            resources: [
              loggingConfigFunction.function.functionArn
            ]
          })
        ]
      })

    const frameworkOnEventRole = new Role(this, `${props.stackName}BedrockLoggingProviderFrameworkOnEventRole`, {
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
      description: "Execution role for bedrock logging provider framework onEvent Lambda function",
      managedPolicies: [
        putLogsManagedPolicy,
        cloudwatchEncryptionKMSPolicy,
        frameworkInvokeBedrockLoggingPolicy
      ]
    })

    const frameworkOnEventRoleRef = Role.fromRoleArn(
      this,
      `${props.stackName}OnEventRoleRef`,
      frameworkOnEventRole.roleArn,
      {mutable: false}
    )
    // Create custom resource provider
    const provider = new Provider(this, "LoggingConfigProvider", {
      onEventHandler: loggingConfigFunction.function,
      logGroup: modelInvocationLogGroup,
      frameworkOnEventRole: frameworkOnEventRoleRef
    })

    // Create custom resource
    new CustomResource(this, "BedrockLoggingConfig", {
      serviceToken: provider.serviceToken
    })

    this.modelInvocationLogGroup = modelInvocationLogGroup
    this.bedrockLoggingRole = bedrockLoggingRole
  }
}
