import {
  App,
  Fn,
  Stack,
  StackProps
} from "aws-cdk-lib"
import {basePathMappingNagSuppressions} from "../nagSuppressions"
import {BasePathMapping, RestApi, DomainName} from "aws-cdk-lib/aws-apigateway"
import {StringParameter} from "aws-cdk-lib/aws-ssm"

export interface EpsAssistMe_BasepathMappingProps extends StackProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
  readonly statefulStackName: string
  readonly statelessStackName: string
}

export class EpsAssistMe_BasepathMapping extends Stack {
  public constructor(scope: App, id: string, props: EpsAssistMe_BasepathMappingProps) {
    super(scope, id, props)

    // imports
    const domainImport = Fn.importValue(`${props.statefulStackName}:domain:Name`)
    //const apiGatewayId = Fn.importValue(`${props.statelessStackName}:apiGateway:api:RestApiId`)
    const apiGatewayId = StringParameter.valueForStringParameter(
      this,
      `${props.statelessStackName}/apiGateway/restApiId`
    )
    const domain = DomainName.fromDomainNameAttributes(this, "ApiDomainName", {
      domainName: domainImport,
      domainNameAliasTarget: "", // not needed for base path mapping
      domainNameAliasHostedZoneId: "" // not needed for base path mapping
    })
    const apiGateway = RestApi.fromRestApiId(this, "ImportedApiGateway", apiGatewayId)

    // Get variables from context
    const account = Stack.of(this).account

    new BasePathMapping(this, "BasePathMapping", {
      domainName: domain,
      restApi: apiGateway,
      stage: apiGateway.deploymentStage
    })
    // Final CDK Nag Suppressions
    basePathMappingNagSuppressions(this, account)
  }
}
