import {Construct} from "constructs"
import {Duration, Fn, RemovalPolicy} from "aws-cdk-lib"
import {
  ManagedPolicy,
  PolicyStatement,
  Role,
  ServicePrincipal,
  IManagedPolicy
} from "aws-cdk-lib/aws-iam"
import {Key} from "aws-cdk-lib/aws-kms"
import {Stream} from "aws-cdk-lib/aws-kinesis"
import {
  Architecture,
  CfnFunction,
  LayerVersion,
  Runtime,
  Function as LambdaFunctionResource,
  Code
} from "aws-cdk-lib/aws-lambda"
import {CfnLogGroup, CfnSubscriptionFilter, LogGroup} from "aws-cdk-lib/aws-logs"

export interface LambdaFunctionProps {
  readonly stackName: string
  readonly functionName: string
  readonly packageBasePath: string
  readonly entryPoint: string
  readonly environmentVariables: {[key: string]: string}
  readonly additionalPolicies?: Array<IManagedPolicy>
  readonly role?: Role
  readonly logRetentionInDays: number
  readonly logLevel: string
}

// Lambda Insights layer for enhanced monitoring
const insightsLayerArn = "arn:aws:lambda:eu-west-2:580247275435:layer:LambdaInsightsExtension:55"

export class LambdaFunction extends Construct {
  public readonly executionPolicy: ManagedPolicy
  public readonly function: LambdaFunctionResource

  public constructor(scope: Construct, id: string, props: LambdaFunctionProps) {
    super(scope, id)

    // Import shared cloud resources from cross-stack references
    const cloudWatchLogsKmsKey = Key.fromKeyArn(
      this, "cloudWatchLogsKmsKey", Fn.importValue("account-resources:CloudwatchLogsKmsKeyArn"))

    const cloudwatchEncryptionKMSPolicy = ManagedPolicy.fromManagedPolicyArn(
      this, "cloudwatchEncryptionKMSPolicyArn", Fn.importValue("account-resources:CloudwatchEncryptionKMSPolicyArn"))

    const splunkDeliveryStream = Stream.fromStreamArn(
      this, "SplunkDeliveryStream", Fn.importValue("lambda-resources:SplunkDeliveryStream"))

    const splunkSubscriptionFilterRole = Role.fromRoleArn(
      this, "splunkSubscriptionFilterRole", Fn.importValue("lambda-resources:SplunkSubscriptionFilterRole"))

    const lambdaInsightsLogGroupPolicy = ManagedPolicy.fromManagedPolicyArn(
      this, "lambdaInsightsLogGroupPolicy", Fn.importValue("lambda-resources:LambdaInsightsLogGroupPolicy"))

    const insightsLambdaLayer = LayerVersion.fromLayerVersionArn(
      this, "LayerFromArn", insightsLayerArn)

    // Log group with encryption and retention
    const logGroup = new LogGroup(this, "LambdaLogGroup", {
      encryptionKey: cloudWatchLogsKmsKey,
      logGroupName: `/aws/lambda/${props.functionName!}`,
      retention: props.logRetentionInDays,
      removalPolicy: RemovalPolicy.DESTROY
    })

    // Suppress CFN guard rules for log group
    const cfnlogGroup = logGroup.node.defaultChild as CfnLogGroup
    cfnlogGroup.cfnOptions.metadata = {
      guard: {
        SuppressedRules: [
          "CW_LOGGROUP_RETENTION_PERIOD_CHECK"
        ]
      }
    }

    // Send logs to Splunk
    new CfnSubscriptionFilter(this, "LambdaLogsSplunkSubscriptionFilter", {
      destinationArn: splunkDeliveryStream.streamArn,
      filterPattern: "",
      logGroupName: logGroup.logGroupName,
      roleArn: splunkSubscriptionFilterRole.roleArn
    })

    // Create managed policy for Lambda CloudWatch logs access
    const putLogsManagedPolicy = new ManagedPolicy(this, "LambdaPutLogsManagedPolicy", {
      description: `write to ${props.functionName} logs`,
      statements: [
        new PolicyStatement({
          actions: [
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ],
          resources: [
            logGroup.logGroupArn,
            `${logGroup.logGroupArn}:log-stream:*`
          ]
        })
      ]
    })

    // Aggregate all required policies for Lambda execution
    const requiredPolicies: Array<IManagedPolicy> = [
      putLogsManagedPolicy,
      lambdaInsightsLogGroupPolicy,
      cloudwatchEncryptionKMSPolicy,
      ...(props.additionalPolicies ?? [])
    ]

    // Use provided role or create new one with required policies
    let role: Role
    if (props.role) {
      role = props.role
      // Attach any missing managed policies to the provided role
      for (const policy of requiredPolicies) {
        role.addManagedPolicy(policy)
      }
    } else {
      role = new Role(this, "LambdaRole", {
        assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
        managedPolicies: requiredPolicies
      })
    }

    // Create Lambda function with Python runtime and monitoring
    const lambdaFunction = new LambdaFunctionResource(this, props.functionName, {
      runtime: Runtime.PYTHON_3_13,
      memorySize: 256,
      timeout: Duration.seconds(50),
      architecture: Architecture.X86_64,
      handler: "app.handler",
      code: Code.fromAsset(`.build/${props.functionName}`),
      role,
      environment: {
        ...props.environmentVariables,
        LOG_LEVEL: props.logLevel
      },
      logGroup,
      layers: [insightsLambdaLayer]
    })

    // Suppress CFN guard rules for Lambda function
    const cfnLambda = lambdaFunction.node.defaultChild as CfnFunction
    cfnLambda.cfnOptions.metadata = {
      guard: {
        SuppressedRules: [
          "LAMBDA_DLQ_CHECK",
          "LAMBDA_INSIDE_VPC",
          "LAMBDA_CONCURRENCY_CHECK"
        ]
      }
    }

    // Create policy for external services to invoke this Lambda
    const executionManagedPolicy = new ManagedPolicy(this, "ExecuteLambdaManagedPolicy", {
      description: `execute lambda ${props.functionName}`,
      statements: [
        new PolicyStatement({
          actions: ["lambda:InvokeFunction"],
          resources: [lambdaFunction.functionArn]
        })
      ]
    })

    // Export Lambda function and execution policy for use by other constructs
    this.function = lambdaFunction
    this.executionPolicy = executionManagedPolicy
  }
}
