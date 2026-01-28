import {Construct} from "constructs"
import {RestApiGateway} from "../constructs/RestApiGateway"
import {LambdaEndpoint} from "../constructs/RestApiGateway/LambdaEndpoint"
import {LambdaFunction} from "../constructs/LambdaFunction"
import {HttpMethod} from "aws-cdk-lib/aws-lambda"

export interface ApisProps {
  readonly stackName: string
  readonly logRetentionInDays: number
  functions: {[key: string]: LambdaFunction}
  readonly forwardCsocLogs: boolean
  readonly csocApiGatewayDestination: string
}

export class Apis extends Construct {
  public apiGateway: RestApiGateway

  public constructor(scope: Construct, id: string, props: ApisProps) {
    super(scope, id)

    // Create REST API Gateway for EPS Assist endpoints
    const apiGateway = new RestApiGateway(this, "EpsAssistApiGateway", {
      stackName: props.stackName,
      logRetentionInDays: props.logRetentionInDays,
      trustStoreKey: "unused",
      truststoreVersion: "unused",
      forwardCsocLogs: props.forwardCsocLogs,
      csocApiGatewayDestination: props.csocApiGatewayDestination
    })
    // Create /slack resource path
    const slackResource = apiGateway.api.root.addResource("slack")

    // Create the '/slack/events' POST endpoint for Slack Events API
    // This endpoint will handle @mentions, direct messages, and other Slack events
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const slackEventsEndpoint = new LambdaEndpoint(this, "SlackEventsEndpoint", {
      parentResource: slackResource,
      resourceName: "events",
      method: HttpMethod.POST,
      restApiGatewayRole: apiGateway.role,
      lambdaFunction: props.functions.slackBot
    })

    this.apiGateway = apiGateway
  }
}
