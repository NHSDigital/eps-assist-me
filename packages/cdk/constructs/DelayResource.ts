import {Construct} from "constructs"
import {CustomResource} from "aws-cdk-lib"
import {Provider} from "aws-cdk-lib/custom-resources"
import {PythonLambdaFunction} from "@nhsdigital/eps-cdk-constructs"
import {resolve} from "path"

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
   * Name prefix for the delay Lambda function
   */
  readonly functionName: string

  /**
   * The number of days to retain logs in CloudWatch Logs
   */
  readonly logRetentionInDays: number

  /**
   * The log level for the delay Lambda function
   */
  readonly logLevel: string
}

/**
 * a fix for an annoying time sync issue that adds a configurable delay
 * to ensure AWS resources are fully available before dependent resources are created
 */
export class DelayResource extends Construct {
  public readonly customResource: CustomResource
  public readonly delaySeconds: number

  constructor(scope: Construct, id: string, props: DelayResourceProps) {
    super(scope, id)

    this.delaySeconds = props.delaySeconds || 30

    // create the delay Lambda function using PythonLambdaFunction for standard monitoring
    const delayFunction = new PythonLambdaFunction(this, "DelayFunction", {
      functionName: props.functionName,
      projectBaseDir: resolve(__dirname, "../../.."),
      packageBasePath: "packages/delayFunction",
      handler: "app.handler.handler",
      logRetentionInDays: props.logRetentionInDays,
      logLevel: props.logLevel,
      timeoutInSeconds: 900 // max Lambda timeout to handle long delays
    })

    // create the custom resource provider
    const provider = new Provider(this, "DelayProvider", {
      onEventHandler: delayFunction.function
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
