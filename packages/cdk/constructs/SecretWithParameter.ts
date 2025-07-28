import {Construct} from "constructs"
import {SecretValue} from "aws-cdk-lib"
import {StringParameter, ParameterTier} from "aws-cdk-lib/aws-ssm"
import {Secret} from "aws-cdk-lib/aws-secretsmanager"

export interface SecretWithParameterProps {
  secretName: string
  parameterName: string
  description: string
  secretValue: string
}

export class SecretWithParameter extends Construct {
  public readonly secret: Secret
  public readonly parameter: StringParameter

  constructor(scope: Construct, id: string, props: SecretWithParameterProps) {
    super(scope, id)

    this.secret = new Secret(this, "Secret", {
      secretName: props.secretName,
      description: props.description,
      secretStringValue: SecretValue.unsafePlainText(props.secretValue)
    })

    this.parameter = new StringParameter(this, "Parameter", {
      parameterName: props.parameterName,
      stringValue: `{{resolve:secretsmanager:${this.secret.secretName}}}`,
      description: `Reference to ${props.description}`,
      tier: ParameterTier.STANDARD
    })
  }
}
