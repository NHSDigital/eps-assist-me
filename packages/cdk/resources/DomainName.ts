import {Fn} from "aws-cdk-lib"
import {DomainName, EndpointType, SecurityPolicy} from "aws-cdk-lib/aws-apigateway"
import {Construct} from "constructs"
import {Certificate, CertificateValidation} from "aws-cdk-lib/aws-certificatemanager"
import {
  ARecord,
  AaaaRecord,
  HostedZone,
  RecordTarget
} from "aws-cdk-lib/aws-route53"
import {ApiGatewayDomain} from "aws-cdk-lib/aws-route53-targets"

export interface ApiDomainNameProps {
  readonly apiGatewayDomainName: string
}

export class ApiDomainName extends Construct {
  public readonly domain: DomainName

  public constructor(scope: Construct, id: string, props: ApiDomainNameProps) {
    super(scope, id)

    // Imports

    const epsDomainName: string = Fn.importValue("eps-route53-resources:EPS-domain")
    const hostedZone = HostedZone.fromHostedZoneAttributes(this, "HostedZone", {
      hostedZoneId: Fn.importValue("eps-route53-resources:EPS-ZoneID"),
      zoneName: epsDomainName
    })
    const serviceDomainName = `${props.apiGatewayDomainName}.${epsDomainName}`

    // Resources

    const certificate = new Certificate(this, "Certificate", {
      domainName: serviceDomainName,
      validation: CertificateValidation.fromDns(hostedZone)
    })

    const domain = new DomainName(this, "ApiDomain", {
      domainName: serviceDomainName,
      certificate,
      securityPolicy: SecurityPolicy.TLS_1_2,
      endpointType: EndpointType.REGIONAL
    })

    new ARecord(this, "ARecord", {
      recordName: props.stackName,
      target: RecordTarget.fromAlias(new ApiGatewayDomain(domain)),
      zone: hostedZone
    })

    new AaaaRecord(this, "AAAARecord", {
      recordName: props.stackName,
      target: RecordTarget.fromAlias(new ApiGatewayDomain(domain)),
      zone: hostedZone
    })

    // Outputs
    this.domain = domain
  }
}
