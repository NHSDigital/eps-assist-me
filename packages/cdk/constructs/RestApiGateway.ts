import {Fn, RemovalPolicy} from "aws-cdk-lib"
import {
  CfnStage,
  EndpointType,
  LogGroupLogDestination,
  MethodLoggingLevel,
  RestApi
} from "aws-cdk-lib/aws-apigateway"
import {IRole, Role, ServicePrincipal} from "aws-cdk-lib/aws-iam"
import {Stream} from "aws-cdk-lib/aws-kinesis"
import {Key} from "aws-cdk-lib/aws-kms"
import {CfnSubscriptionFilter, LogGroup} from "aws-cdk-lib/aws-logs"
import {Construct} from "constructs"
import {accessLogFormat} from "./RestApiGateway/accessLogFormat"
import {addSuppressions} from "@nhsdigital/eps-cdk-constructs"

export interface RestApiGatewayProps {
  readonly stackName: string
  readonly logRetentionInDays: number
  readonly trustStoreKey: string
  readonly truststoreVersion: string
  readonly forwardCsocLogs: boolean
  readonly csocApiGatewayDestination: string
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

    if (props.forwardCsocLogs) {
      new CfnSubscriptionFilter(this, "ApiGatewayAccessLogsCSOCSubscriptionFilter", {
        destinationArn: props.csocApiGatewayDestination,
        filterPattern: "",
        logGroupName: logGroup.logGroupName,
        roleArn: splunkSubscriptionFilterRole.roleArn
      })
    }

    const apiGateway = new RestApi(this, "ApiGateway", {
      restApiName: `${props.stackName}-apigw`,
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

    const cfnStage = apiGateway.deploymentStage.node.defaultChild as CfnStage
    addSuppressions([cfnStage], [
      "API_GW_CACHE_ENABLED_AND_ENCRYPTED"
    ])

    // Outputs
    this.api = apiGateway
    this.role = role
  }
}
