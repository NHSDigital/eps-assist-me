import {
  RestApi,
  EndpointType,
  SecurityPolicy,
  LogGroupLogDestination,
  MethodLoggingLevel,
  CfnStage
} from "aws-cdk-lib/aws-apigateway"
import {Construct} from "constructs"
import {RetentionDays, LogGroup} from "aws-cdk-lib/aws-logs"
import {Key} from "aws-cdk-lib/aws-kms"
import {Fn, RemovalPolicy} from "aws-cdk-lib"
import {Role, ServicePrincipal} from "aws-cdk-lib/aws-iam"
import {Certificate, CertificateValidation} from "aws-cdk-lib/aws-certificatemanager"
import {HostedZone, ARecord, RecordTarget} from "aws-cdk-lib/aws-route53"
import {ApiGateway as ApiGatewayTarget} from "aws-cdk-lib/aws-route53-targets"

export interface RestApiGatewayProps {
  readonly stackName: string
  readonly logRetentionInDays: number
  readonly enableMutualTls: boolean
  readonly trustStoreKey: string
  readonly truststoreVersion: string
}

export class RestApiGateway extends Construct {
  public readonly api: RestApi
  public readonly role: Role

  constructor(scope: Construct, id: string, props: RestApiGatewayProps) {
    super(scope, id)

    const domainName = Fn.importValue("eps-route53-resources:EPS-domain")
    const zoneId = Fn.importValue("eps-route53-resources:EPS-ZoneID")

    const hostedZone = HostedZone.fromHostedZoneAttributes(this, "HostedZone", {
      hostedZoneId: zoneId,
      zoneName: domainName
    })

    const serviceDomain = `${props.stackName}.${domainName}`

    const certificate = new Certificate(this, "TlsCert", {
      domainName: serviceDomain,
      validation: CertificateValidation.fromDns(hostedZone)
    })

    const logGroup = new LogGroup(this, "ApiGwLogs", {
      logGroupName: `/aws/apigateway/${props.stackName}-apigw`,
      retention: RetentionDays.TWO_WEEKS,
      removalPolicy: RemovalPolicy.DESTROY
    })

    this.api = new RestApi(this, "RestApi", {
      restApiName: `${props.stackName}-api`,
      deployOptions: {
        accessLogDestination: new LogGroupLogDestination(logGroup),
        accessLogFormat: undefined,
        loggingLevel: MethodLoggingLevel.INFO,
        metricsEnabled: true
      },
      domainName: {
        domainName: serviceDomain,
        certificate: certificate,
        endpointType: EndpointType.REGIONAL,
        securityPolicy: SecurityPolicy.TLS_1_2
      }
    })

    new ARecord(this, "DnsRecord", {
      zone: hostedZone,
      recordName: props.stackName,
      target: RecordTarget.fromAlias(new ApiGatewayTarget(this.api))
    })

    this.role = new Role(this, "ApiGatewayRole", {
      assumedBy: new ServicePrincipal("apigateway.amazonaws.com")
    })

    const cfnStage = this.api.deploymentStage.node.defaultChild as CfnStage
    cfnStage.cfnOptions.metadata = {
      guard: {SuppressedRules: ["API_GW_CACHE_ENABLED_AND_ENCRYPTED"]}
    }
  }
}
