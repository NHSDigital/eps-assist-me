import {Construct} from "constructs"
import {Duration, CustomResource} from "aws-cdk-lib"
import {Function, Runtime, Code} from "aws-cdk-lib/aws-lambda"
import {
  Role,
  ServicePrincipal,
  PolicyDocument,
  PolicyStatement,
  Effect
} from "aws-cdk-lib/aws-iam"
import {Provider} from "aws-cdk-lib/custom-resources"

export interface DelayResourceProps {
  /**
   * The delay time in seconds (default: 30 seconds)
   */
  readonly delaySeconds?: number

  /**
   * Optional description for the delay resource
   */
  readonly description?: string
}

/**
 * a fix for an annoying time sync issue that adds a configurable delay
 * to ensure AWS resources are fully available before dependent resources are created
 */
export class DelayResource extends Construct {
  public readonly customResource: CustomResource
  public readonly delaySeconds: number

  constructor(scope: Construct, id: string, props: DelayResourceProps = {}) {
    super(scope, id)

    this.delaySeconds = props.delaySeconds || 30

    // create IAM role for the delay Lambda function
    const lambdaExecutionRole = new Role(this, "LambdaExecutionRole", {
      assumedBy: new ServicePrincipal("lambda.amazonaws.com"),
      description: "Execution role for delay custom resource Lambda function",
      inlinePolicies: {
        LogsPolicy: new PolicyDocument({
          statements: [
            new PolicyStatement({
              effect: Effect.ALLOW,
              actions: [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
              ],
              resources: ["*"]
            })
          ]
        })
      }
    })

    // create the delay Lambda function with inline Python code
    const delayFunction = new Function(this, "DelayFunction", {
      runtime: Runtime.PYTHON_3_12,
      handler: "index.handler",
      role: lambdaExecutionRole,
      timeout: Duration.minutes(15), // max Lambda timeout to handle long delays
      description: props.description || `Delay resource for ${this.delaySeconds} seconds`,
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
        if event["RequestType"] in ["Create", "Update"]:
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

    // create the custom resource provider
    const provider = new Provider(this, "DelayProvider", {
      onEventHandler: delayFunction
    })

    // create the custom resource that triggers the delay
    this.customResource = new CustomResource(this, "DelayCustomResource", {
      serviceToken: provider.serviceToken,
      properties: {
        WaitSeconds: this.delaySeconds,
        Description: props.description || `Delay for ${this.delaySeconds} seconds`,
        // timestamp to ensure updates trigger when properties change
        Timestamp: Date.now()
      }
    })
  }

}
