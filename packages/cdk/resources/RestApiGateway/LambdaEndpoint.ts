import {Construct} from "constructs"
import {IResource, LambdaIntegration} from "aws-cdk-lib/aws-apigateway"
import {HttpMethod} from "aws-cdk-lib/aws-lambda"
import {IRole} from "aws-cdk-lib/aws-iam"
import {LambdaFunction} from "../LambdaFunction"

// Props for constructing an API Gateway endpoint backed by a Lambda function.
export interface LambdaEndpointProps {
  readonly parentResource: IResource
  readonly resourceName: string
  readonly method: HttpMethod
  readonly restApiGatewayRole: IRole
  readonly lambdaFunction: LambdaFunction
}

// Creates an API Gateway resource and method integrated with a Lambda function.
export class LambdaEndpoint extends Construct {
  public readonly resource: IResource

  constructor(scope: Construct, id: string, props: LambdaEndpointProps) {
    super(scope, id)

    // Add a new resource to the parent resource
    const resource = props.parentResource.addResource(props.resourceName)

    // Add a method to the resource, integrated with the Lambda function.
    resource.addMethod(props.method, new LambdaIntegration(props.lambdaFunction.function))

    // Grant API Gateway's role permission to invoke the Lambda function.
    props.lambdaFunction.function.grantInvoke(props.restApiGatewayRole)

    // Expose the resource for potential further use.
    this.resource = resource
  }
}
