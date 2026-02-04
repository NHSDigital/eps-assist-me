import {Construct} from "constructs"
import {
  Duration,
  CustomResource,
  Fn,
  RemovalPolicy
} from "aws-cdk-lib"
import {Function, Runtime, Code} from "aws-cdk-lib/aws-lambda"
import {
  Role,
  ServicePrincipal,
  ManagedPolicy,
  PolicyStatement
} from "aws-cdk-lib/aws-iam"
import {Provider} from "aws-cdk-lib/custom-resources"
import {Key} from "aws-cdk-lib/aws-kms"
import {CfnLogGroup, LogGroup} from "aws-cdk-lib/aws-logs"
import {addSuppressions} from "@nhsdigital/eps-cdk-constructs"
import {NagSuppressions} from "cdk-nag"

export interface DelayResourceProps {
  /**
   * The delay time in seconds (default: 30 seconds)
   */
  readonly delaySeconds?: number

  /**
   * Optional description for the delay resource
   */
  readonly description?: string

  /**
   * Name for the delay resource
   */
  readonly name: string
}

/**
 * a fix for an annoying time sync issue that adds a configurable delay
 * to ensure AWS resources are fully available before dependent resources are created
 */
export class DelayResource extends Construct {
  public readonly customResource: CustomResource

  constructor(scope: Construct, id: string, props: DelayResourceProps) {
    super(scope, id)
    const {
      delaySeconds = 30,
      description = `Delay resource for ${delaySeconds} seconds`,
      name
    } = props
    const cloudWatchLogsKmsKey = Key.fromKeyArn(
      scope, `${name}delayResourceCloudWatchLogsKmsKey`, Fn.importValue("account-resources:CloudwatchLogsKmsKeyArn"))

    const cloudwatchEncryptionKMSPolicy = ManagedPolicy.fromManagedPolicyArn(
      scope, `${name}delayResourceCloudwatchEncryptionKMSPolicyArn`,
      Fn.importValue("account-resources:CloudwatchEncryptionKMSPolicyArn"))

    const logGroup = new LogGroup(scope, `${name}LambdaLogGroup`, {
      encryptionKey: cloudWatchLogsKmsKey,
      logGroupName: `/aws/lambda/${name}`,
      retention: 30,
      removalPolicy: RemovalPolicy.DESTROY
    })

    const cfnlogGroup = logGroup.node.defaultChild as CfnLogGroup
    addSuppressions([cfnlogGroup], ["CW_LOGGROUP_RETENTION_PERIOD_CHECK"])
    const putLogsManagedPolicy = new ManagedPolicy(scope, `${name}LambdaPutLogsManagedPolicy`, {
      description: `write to ${name} logs`,
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

    NagSuppressions.addResourceSuppressions(putLogsManagedPolicy, [
      {
        id: "AwsSolutions-IAM5",
        // eslint-disable-next-line max-len
        reason: "Suppress error for not having wildcards in permissions. This is a fine as we need to have permissions on all log streams under path"
      }
    ])

    // create IAM role for the delay Lambda function
    const lambdaExecutionRole = new Role(this, `${name}LambdaExecutionRole`, {
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
      description: "Execution role for delay custom resource Lambda function",
      managedPolicies: [
        putLogsManagedPolicy,
        cloudwatchEncryptionKMSPolicy
      ]
    })

    // create the delay Lambda function with inline Python code
    const delayFunction = new Function(this, `${name}DelayFunction`, {
      runtime: Runtime.PYTHON_3_12,
      logGroup: logGroup,
      handler: "index.handler",
      role: lambdaExecutionRole,
      timeout: Duration.minutes(15), // max Lambda timeout to handle long delays
      description: description,
      code: Code.fromInline(`
from time import sleep
import json
import cfnresponse
import uuid

def handler(event, context):
    wait_seconds = 0
    id = str(uuid.uuid1())

    print(f"Received event: {json.dumps(event, default=str)}")

    try:
        if event["RequestType"] in ["Create"]:
            wait_seconds = int(event["ResourceProperties"].get("WaitSeconds", 0))
            print(f"Waiting for {wait_seconds} seconds...")
            sleep(wait_seconds)
            print(f"Wait complete")

        response = {
            "TimeWaited": wait_seconds,
            "Id": id,
            "Status": "SUCCESS"
        }

        cfnresponse.send(event, context, cfnresponse.SUCCESS, response, f"Waiter-{id}")

    except Exception as e:
        print(f"Error: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {"Error": str(e)}, f"Waiter-{id}")
`)
    })

    const frameworkInvokeDelayFunctionPolicy = new ManagedPolicy(this,
      `${name}DelayProviderInvokeDelayFunctionPolicy`, {
        description: `Allow provider framework to invoke ${name} delay function`,
        statements: [
          new PolicyStatement({
            actions: [
              "lambda:InvokeFunction",
              "lambda:GetFunction"
            ],
            resources: [
              delayFunction.functionArn
            ]
          })
        ]
      })

    const frameworkOnEventRole = new Role(this, `${name}DelayProviderFrameworkOnEventRole`, {
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
      description: "Execution role for delay provider framework onEvent Lambda function",
      managedPolicies: [
        putLogsManagedPolicy,
        cloudwatchEncryptionKMSPolicy,
        frameworkInvokeDelayFunctionPolicy
      ]
    })

    const frameworkOnEventRoleRef = Role.fromRoleArn(
      this,
      `${name}DelayProviderFrameworkOnEventRoleRef`,
      frameworkOnEventRole.roleArn,
      {mutable: false}
    )

    // create the custom resource provider
    const provider = new Provider(this, `${name}DelayProvider`, {
      onEventHandler: delayFunction,
      logGroup: logGroup,
      frameworkOnEventRole: frameworkOnEventRoleRef
    })

    // create the custom resource that triggers the delay
    this.customResource = new CustomResource(this, `${name}DelayCustomResource`, {
      serviceToken: provider.serviceToken,
      properties: {
        WaitSeconds: delaySeconds,
        Description: description,
        // timestamp to ensure updates trigger when properties change
        Timestamp: Date.now()
      }
    })
  }

}
