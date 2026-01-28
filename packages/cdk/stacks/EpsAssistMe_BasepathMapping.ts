import {
  App,
  Stack,
  StackProps,
  Fn
} from "aws-cdk-lib"
import {nagSuppressions} from "../nagSuppressions"
import {BasePathMapping, RestApi, DomainName} from "aws-cdk-lib/aws-apigateway"

export interface EpsAssistMe_BasepathMappingProps extends StackProps {
  readonly stackName: string
  readonly version: string
  readonly commitId: string
}

export class EpsAssistMe_BasepathMapping extends Stack {
  public constructor(scope: App, id: string, props: EpsAssistMe_BasepathMappingProps) {
    super(scope, id, props)

    // imports
    const domainImport = Fn.importValue("<CHANGE ME>")
    const apiGatewayId = Fn.importValue("<CHANGE ME>")

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
    nagSuppressions(this, account)
  }
}
