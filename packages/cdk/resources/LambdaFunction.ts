import {Construct} from "constructs"
import {Duration, Fn, RemovalPolicy} from "aws-cdk-lib"
import {
  ManagedPolicy,
  PolicyStatement,
  Role,
  ServicePrincipal,
  IManagedPolicy
} from "aws-cdk-lib/aws-iam"
import * as lambda from "aws-cdk-lib/aws-lambda"
import {Key} from "aws-cdk-lib/aws-kms"
import {Stream} from "aws-cdk-lib/aws-kinesis"
import {
  Architecture,
  CfnFunction,
  LayerVersion,
  Runtime
} from "aws-cdk-lib/aws-lambda"
import {CfnLogGroup, CfnSubscriptionFilter, LogGroup} from "aws-cdk-lib/aws-logs"
import {join, resolve} from "path"
import {existsSync} from "fs"
import {execSync} from "child_process"

export interface LambdaFunctionProps {
  readonly stackName: string
  readonly functionName: string
  readonly packageBasePath: string
  readonly entryPoint: string
  readonly environmentVariables: {[key: string]: string}
  readonly additionalPolicies?: Array<IManagedPolicy>
  readonly logRetentionInDays: number
  readonly logLevel: string
}

const insightsLayerArn = "arn:aws:lambda:eu-west-2:580247275435:layer:LambdaInsightsExtension:55"

export class LambdaFunction extends Construct {
  public readonly executionPolicy: ManagedPolicy
  public readonly function: lambda.Function

  public constructor(scope: Construct, id: string, props: LambdaFunctionProps) {
    super(scope, id)

    // Shared cloud resources
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

    // IAM role and policy for the Lambda
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

    const role = new Role(this, "LambdaRole", {
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        putLogsManagedPolicy,
        lambdaInsightsLogGroupPolicy,
        cloudwatchEncryptionKMSPolicy,
        ...(props.additionalPolicies ?? [])
      ]
    })

    // Define the Lambda function
    const lambdaFunction = new lambda.Function(this, props.functionName, {
      runtime: Runtime.PYTHON_3_13,
      memorySize: 256,
      timeout: Duration.seconds(50),
      architecture: Architecture.X86_64,
      handler: "handler",
      code: lambda.Code.fromAsset(props.packageBasePath, {
        bundling: {
          image: lambda.Runtime.PYTHON_3_13.bundlingImage,
          local: {
            tryBundle(outputDir: string) {
              try {
                execSync("pip3 --version", {stdio: "inherit"})
              } catch {
                return false
              }

              const cwd = resolve(props.packageBasePath)
              const commands = []

              if (existsSync(join(cwd, "requirements.txt"))) {
                commands.push(`pip3 install -r requirements.txt -t ${outputDir}`)
              }

              commands.push(`cp -a . ${outputDir}`)

              execSync(commands.join(" && "), {cwd, stdio: "inherit"})

              return true
            }
          }
        }
      }),
      role,
      environment: {
        ...props.environmentVariables,
        LOG_LEVEL: props.logLevel
      },
      logGroup,
      layers: [insightsLambdaLayer]
    })

    // Guard rule suppressions (can be removed after full compliance)
    const cfnLambda = lambdaFunction.node.defaultChild as CfnFunction
    cfnLambda.cfnOptions.metadata = {
      guard: {
        SuppressedRules: [
          "LAMBDA_CONCURRENCY_CHECK"
        ]
      }
    }

    // Policy to allow invoking this Lambda
    const executionManagedPolicy = new ManagedPolicy(this, "ExecuteLambdaManagedPolicy", {
      description: `execute lambda ${props.functionName}`,
      statements: [
        new PolicyStatement({
          actions: ["lambda:InvokeFunction"],
          resources: [lambdaFunction.functionArn]
        })
      ]
    })

    // Outputs
    this.function = lambdaFunction
    this.executionPolicy = executionManagedPolicy
  }
}
