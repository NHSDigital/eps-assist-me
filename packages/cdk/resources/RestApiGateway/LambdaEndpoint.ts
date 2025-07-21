import {Construct} from "constructs"
import {IResource, LambdaIntegration} from "aws-cdk-lib/aws-apigateway"
import {HttpMethod} from "aws-cdk-lib/aws-lambda"
import {LambdaFunction} from "../LambdaFunction"

export interface LambdaEndpointProps {
  readonly parentResource: IResource
  readonly resourceName: string
  readonly method: HttpMethod
  readonly lambdaFunction: LambdaFunction
}

// Creates an API Gateway resource and method integrated with a Lambda function
export class LambdaEndpoint extends Construct {
  public readonly resource: IResource

  constructor(scope: Construct, id: string, props: LambdaEndpointProps) {
    super(scope, id)

    // Add a new resource to the parent resource
    const resource = props.parentResource.addResource(props.resourceName)

    // Let CDK/APIGateway manage the Lambda invoke permission automatically
    resource.addMethod(props.method, new LambdaIntegration(props.lambdaFunction.function))

    this.resource = resource
  }
}
