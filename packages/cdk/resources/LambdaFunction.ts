import {Construct} from "constructs"
import {Duration, Fn, RemovalPolicy} from "aws-cdk-lib"
import {Runtime} from "aws-cdk-lib/aws-lambda"
import {
  ManagedPolicy,
  PolicyStatement,
  Role,
  ServicePrincipal,
  IManagedPolicy
} from "aws-cdk-lib/aws-iam"
import {PythonFunction} from "@aws-cdk/aws-lambda-python-alpha"
import {LogGroup, RetentionDays} from "aws-cdk-lib/aws-logs"

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

export class LambdaFunction extends Construct {
  public readonly function: PythonFunction
  public readonly executionPolicy: ManagedPolicy

  constructor(scope: Construct, id: string, props: LambdaFunctionProps) {
    super(scope, id)

    const lambdaDecryptSecretsKMSPolicy = ManagedPolicy.fromManagedPolicyArn(
      this, "lambdaDecryptSecretsKMSPolicy",
      Fn.importValue("account-resources:LambdaDecryptSecretsKMSPolicy")
    )

    const logGroup = new LogGroup(this, `${props.functionName}LogGroup`, {
      logGroupName: `/aws/lambda/${props.functionName}`,
      retention: props.logRetentionInDays,
      removalPolicy: RemovalPolicy.DESTROY
    })

    const role = new Role(this, `${props.functionName}ExecutionRole`, {
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        lambdaDecryptSecretsKMSPolicy,
        ...props.additionalPolicies ?? []
      ]
    })

    const putLogsPolicy = new ManagedPolicy(this, `${props.functionName}PutLogsPolicy`, {
      statements: [
        new PolicyStatement({
          actions: ["logs:CreateLogStream", "logs:PutLogEvents"],
          resources: [logGroup.logGroupArn, `${logGroup.logGroupArn}:*`]
        })
      ]
    })

    role.addManagedPolicy(putLogsPolicy)

    const lambdaFunction = new PythonFunction(this, props.functionName, {
      entry: props.packageBasePath,
      runtime: Runtime.PYTHON_3_12,
      handler: "handler",
      index: props.entryPoint,
      timeout: Duration.seconds(60),
      memorySize: 256,
      role,
      environment: {
        ...props.environmentVariables,
        LOG_LEVEL: props.logLevel
      },
      bundling: {
        command: [
          "bash", "-c",
          // Redirect all stdout and stderr to a log file inside asset-output
          "mkdir -p /asset-output && " + // Ensure /asset-output exists and is writable from the start
          "exec &> /asset-output/bundling-log.txt; " + // Redirect all subsequent output
          "set -ex; " + // Enable immediate exit on error
          'echo "--- Starting bundling process (Deep Dive) ---"; ' +
          'echo "Current working directory: $(pwd)"; ' +
          'echo "Contents of /asset-input:"; ls -al /asset-input; ' +
          'echo "Verifying Python version..."; ' +
          "python3.12 --version; " + // Output captured in log file
          'echo "Creating virtual environment..."; ' +
          "python3.12 -m venv /tmp/lambda-venv; " +
          'echo "Virtual environment created. Listing contents of venv/bin..."; ' +
          "ls -al /tmp/lambda-venv/bin; " +
          'echo "--- Deep Dive Test Complete ---"; ' +
          "exit 0" // Exit cleanly if all goes well
        ]
      }
    })

    this.function = lambdaFunction

    this.executionPolicy = new ManagedPolicy(this, `${props.functionName}InvokePolicy`, {
      statements: [
        new PolicyStatement({
          actions: ["lambda:InvokeFunction"],
          resources: [lambdaFunction.functionArn]
        })
      ]
    })
  }
}
