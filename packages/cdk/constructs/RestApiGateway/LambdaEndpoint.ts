import {Construct} from "constructs"
import {IResource, LambdaIntegration} from "aws-cdk-lib/aws-apigateway"
import {HttpMethod} from "aws-cdk-lib/aws-lambda"
import {IRole, ServicePrincipal} from "aws-cdk-lib/aws-iam"
import {Aws} from "aws-cdk-lib"
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

    const integration = new LambdaIntegration(props.lambdaFunction.function, {
      credentialsRole: props.restApiGatewayRole,
      allowTestInvoke: false,
      proxy: false
    })
    
    resource.addMethod(props.method, integration)
    
    // Add source account to Lambda permission for NCSC compliance
    props.lambdaFunction.function.addPermission(`ApiGatewayInvoke-${this.node.id}`, {
      principal: new ServicePrincipal("apigateway.amazonaws.com"),
      action: "lambda:InvokeFunction",
      sourceAccount: Aws.ACCOUNT_ID
    })

    props.restApiGatewayRole.addManagedPolicy(props.lambdaFunction.executionPolicy)

    this.resource = resource
  }
}
