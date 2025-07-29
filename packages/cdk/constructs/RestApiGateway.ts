import {Fn, RemovalPolicy} from "aws-cdk-lib"
import {
  CfnStage,
  EndpointType,
  LogGroupLogDestination,
  MethodLoggingLevel,
  RestApi,
  SecurityPolicy
} from "aws-cdk-lib/aws-apigateway"
import {IRole, Role, ServicePrincipal} from "aws-cdk-lib/aws-iam"
import {Stream} from "aws-cdk-lib/aws-kinesis"
import {Key} from "aws-cdk-lib/aws-kms"
import {CfnSubscriptionFilter, LogGroup} from "aws-cdk-lib/aws-logs"
import {Construct} from "constructs"
import {accessLogFormat} from "./RestApiGateway/accessLogFormat"
import {Certificate, CertificateValidation} from "aws-cdk-lib/aws-certificatemanager"
import {
  ARecord,
  AaaaRecord,
  HostedZone,
  RecordTarget
} from "aws-cdk-lib/aws-route53"
import {ApiGateway as ApiGatewayTarget} from "aws-cdk-lib/aws-route53-targets"

export interface RestApiGatewayProps {
  readonly stackName: string
  readonly logRetentionInDays: number
  readonly trustStoreKey: string
  readonly truststoreVersion: string
}

export class RestApiGateway extends Construct {
  public readonly api: RestApi
  public readonly role: IRole

  public constructor(scope: Construct, id: string, props: RestApiGatewayProps) {
    super(scope, id)

    // Imports
    const cloudWatchLogsKmsKey = Key.fromKeyArn(
      this, "cloudWatchLogsKmsKey", Fn.importValue("account-resources:CloudwatchLogsKmsKeyArn"))

    const splunkDeliveryStream = Stream.fromStreamArn(
      this, "SplunkDeliveryStream", Fn.importValue("lambda-resources:SplunkDeliveryStream"))

    const splunkSubscriptionFilterRole = Role.fromRoleArn(
      this, "splunkSubscriptionFilterRole", Fn.importValue("lambda-resources:SplunkSubscriptionFilterRole"))

    const epsDomainName: string = Fn.importValue("eps-route53-resources:EPS-domain")
    const hostedZone = HostedZone.fromHostedZoneAttributes(this, "HostedZone", {
      hostedZoneId: Fn.importValue("eps-route53-resources:EPS-ZoneID"),
      zoneName: epsDomainName
    })
    const serviceDomainName = `${props.stackName}.${epsDomainName}`

    // Resources
    const logGroup = new LogGroup(this, "ApiGatewayAccessLogGroup", {
      encryptionKey: cloudWatchLogsKmsKey,
      logGroupName: `/aws/apigateway/${props.stackName}-apigw`,
      retention: props.logRetentionInDays,
      removalPolicy: RemovalPolicy.DESTROY
    })

    new CfnSubscriptionFilter(this, "ApiGatewayAccessLogsSplunkSubscriptionFilter", {
      destinationArn: splunkDeliveryStream.streamArn,
      filterPattern: "",
      logGroupName: logGroup.logGroupName,
      roleArn: splunkSubscriptionFilterRole.roleArn

    })

    const certificate = new Certificate(this, "Certificate", {
      domainName: serviceDomainName,
      validation: CertificateValidation.fromDns(hostedZone)
    })

    const apiGateway = new RestApi(this, "ApiGateway", {
      restApiName: `${props.stackName}-apigw`,
      domainName: {
        domainName: serviceDomainName,
        certificate: certificate,
        securityPolicy: SecurityPolicy.TLS_1_2,
        endpointType: EndpointType.REGIONAL
      },
      endpointConfiguration: {
        types: [EndpointType.REGIONAL]
      },
      deploy: true,
      deployOptions: {
        accessLogDestination: new LogGroupLogDestination(logGroup),
        accessLogFormat: accessLogFormat(),
        loggingLevel: MethodLoggingLevel.INFO,
        metricsEnabled: true
      }
    })

    const role = new Role(this, "ApiGatewayRole", {
      assumedBy: new ServicePrincipal("apigateway.amazonaws.com"),
      managedPolicies: []
    })

    new ARecord(this, "ARecord", {
      recordName: props.stackName,
      target: RecordTarget.fromAlias(new ApiGatewayTarget(apiGateway)),
      zone: hostedZone
    })

    new AaaaRecord(this, "AAAARecord", {
      recordName: props.stackName,
      target: RecordTarget.fromAlias(new ApiGatewayTarget(apiGateway)),
      zone: hostedZone
    })

    const cfnStage = apiGateway.deploymentStage.node.defaultChild as CfnStage
    cfnStage.cfnOptions.metadata = {
      guard: {
        SuppressedRules: [
          "API_GW_CACHE_ENABLED_AND_ENCRYPTED"
        ]
      }
    }

    // Outputs
    this.api = apiGateway
    this.role = role
  }
}
