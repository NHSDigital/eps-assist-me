import {Construct} from "constructs"
import * as cdk from "aws-cdk-lib"
import * as ssm from "aws-cdk-lib/aws-ssm"
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager"

export interface SecretsProps {
  slackBotToken: string
  slackSigningSecret: string
}

export class Secrets extends Construct {
  public readonly slackBotTokenSecret: secretsmanager.Secret
  public readonly slackBotSigningSecret: secretsmanager.Secret
  public readonly slackBotTokenParameter: ssm.StringParameter
  public readonly slackSigningSecretParameter: ssm.StringParameter

  constructor(scope: Construct, id: string, props: SecretsProps) {
    super(scope, id)

    // Create secrets in Secrets Manager
    this.slackBotTokenSecret = new secretsmanager.Secret(this, "SlackBotTokenSecret", {
      secretName: "/eps-assist/slack/bot-token",
      description: "Slack Bot OAuth Token for EPS Assist",
      secretStringValue: cdk.SecretValue.unsafePlainText(JSON.stringify({
        token: props.slackBotToken
      }))
    })

    this.slackBotSigningSecret = new secretsmanager.Secret(this, "SlackBotSigningSecret", {
      secretName: "/eps-assist/slack/signing-secret",
      description: "Slack Signing Secret",
      secretStringValue: cdk.SecretValue.unsafePlainText(JSON.stringify({
        secret: props.slackSigningSecret
      }))
    })

    // Create SSM parameters that reference the secrets
    this.slackBotTokenParameter = new ssm.StringParameter(this, "SlackBotTokenParameter", {
      parameterName: "/eps-assist/slack/bot-token/parameter",
      stringValue: `{{resolve:secretsmanager:${this.slackBotTokenSecret.secretName}}}`,
      description: "Reference to Slack Bot Token in Secrets Manager",
      tier: ssm.ParameterTier.STANDARD
    })

    this.slackSigningSecretParameter = new ssm.StringParameter(this, "SlackSigningSecretParameter", {
      parameterName: "/eps-assist/slack/signing-secret/parameter",
      stringValue: `{{resolve:secretsmanager:${this.slackBotSigningSecret.secretName}}}`,
      description: "Reference to Slack Signing Secret in Secrets Manager",
      tier: ssm.ParameterTier.STANDARD
    })
  }
}
