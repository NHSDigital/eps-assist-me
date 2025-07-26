import {Construct} from "constructs"
import * as cdk from "aws-cdk-lib"
import * as ssm from "aws-cdk-lib/aws-ssm"
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager"

export interface SecretWithParameterProps {
  secretName: string
  parameterName: string
  description: string
  secretValue: string
}

export class SecretWithParameter extends Construct {
  public readonly secret: secretsmanager.Secret
  public readonly parameter: ssm.StringParameter

  constructor(scope: Construct, id: string, props: SecretWithParameterProps) {
    super(scope, id)

    this.secret = new secretsmanager.Secret(this, "Secret", {
      secretName: props.secretName,
      description: props.description,
      secretStringValue: cdk.SecretValue.unsafePlainText(props.secretValue)
    })

    this.parameter = new ssm.StringParameter(this, "Parameter", {
      parameterName: props.parameterName,
      stringValue: `{{resolve:secretsmanager:${this.secret.secretName}}}`,
      description: `Reference to ${props.description}`,
      tier: ssm.ParameterTier.STANDARD
    })
  }
}
