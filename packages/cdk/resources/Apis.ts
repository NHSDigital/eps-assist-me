import {Construct} from "constructs"
import {RestApiGateway} from "../constructs/RestApiGateway"
import {LambdaEndpoint} from "../constructs/RestApiGateway/LambdaEndpoint"
import {LambdaFunction} from "../constructs/LambdaFunction"
import {HttpMethod} from "aws-cdk-lib/aws-lambda"

export interface ApisProps {
  readonly stackName: string
  readonly logRetentionInDays: number
  readonly enableMutalTls: boolean
  functions: {[key: string]: LambdaFunction}
}

export class Apis extends Construct {
  public apis: {[key: string]: RestApiGateway}

  public constructor(scope: Construct, id: string, props: ApisProps) {
    super(scope, id)

    // Create REST API Gateway for EPS Assist endpoints
    const apiGateway = new RestApiGateway(this, "EpsAssistApiGateway", {
      stackName: props.stackName,
      logRetentionInDays: props.logRetentionInDays,
      trustStoreKey: "unused",
      truststoreVersion: "unused"
    })
    // Create /slack resource path
    const slackResource = apiGateway.api.root.addResource("slack")

    // Create the '/slack/ask-eps' POST endpoint and integrate it with the SlackBot Lambda
    new LambdaEndpoint(this, "SlackAskEpsEndpoint", {
      parentResource: slackResource,
      resourceName: "ask-eps",
      method: HttpMethod.POST,
      restApiGatewayRole: apiGateway.role,
      lambdaFunction: props.functions.slackBot
    })
    this.apis = {
      api: apiGateway
    }
  }
}
