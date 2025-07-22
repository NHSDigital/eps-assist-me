import {Construct} from "constructs"
import {IResource, LambdaIntegration} from "aws-cdk-lib/aws-apigateway"
import {HttpMethod} from "aws-cdk-lib/aws-lambda"
import {IRole} from "aws-cdk-lib/aws-iam"
import {LambdaFunction} from "../LambdaFunction"

export interface LambdaEndpointProps {
  readonly parentResource: IResource
  readonly resourceName: string
  readonly method: HttpMethod
  readonly restApiGatewayRole: IRole
  readonly lambdaFunction: LambdaFunction
}

export class LambdaEndpoint extends Construct {
  public readonly resource: IResource

  constructor(scope: Construct, id: string, props: LambdaEndpointProps) {
    super(scope, id)

    const resource = props.parentResource.addResource(props.resourceName)

    resource.addMethod(props.method, new LambdaIntegration(props.lambdaFunction.function, {
      credentialsRole: props.restApiGatewayRole
    }))

    props.restApiGatewayRole.addManagedPolicy(props.lambdaFunction.executionPolicy)

    this.resource = resource
  }
}
