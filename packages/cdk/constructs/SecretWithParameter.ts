import {Construct} from "constructs"
import {SecretValue} from "aws-cdk-lib"
import {StringParameter, ParameterTier} from "aws-cdk-lib/aws-ssm"
import {Secret} from "aws-cdk-lib/aws-secretsmanager"

export interface SecretWithParameterProps {
  readonly secretName: string
  readonly parameterName: string
  readonly description: string
  readonly secretValue: string
}

export class SecretWithParameter extends Construct {
  public readonly secret: Secret
  public readonly parameter: StringParameter

  constructor(scope: Construct, id: string, props: SecretWithParameterProps) {
    super(scope, id)

    // Create secret in AWS Secrets Manager
    const secret = new Secret(this, "Secret", {
      secretName: props.secretName,
      description: props.description,
      secretStringValue: SecretValue.unsafePlainText(props.secretValue)
    })

    // Create SSM parameter that references the secret
    const parameter = new StringParameter(this, "Parameter", {
      parameterName: props.parameterName,
      stringValue: `{{resolve:secretsmanager:${secret.secretName}}}`,
      description: `Reference to ${props.description}`,
      tier: ParameterTier.STANDARD
    })

    this.secret = secret
    this.parameter = parameter
  }
}
