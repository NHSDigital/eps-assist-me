import {Construct} from "constructs"
import {StringParameter} from "aws-cdk-lib/aws-ssm"
import {Secret} from "aws-cdk-lib/aws-secretsmanager"
import {SecretWithParameter} from "../constructs/SecretWithParameter"

export interface SecretsProps {
  slackBotToken: string
  slackSigningSecret: string
}

export class Secrets extends Construct {
  public readonly slackBotTokenSecret: Secret
  public readonly slackBotSigningSecret: Secret
  public readonly slackBotTokenParameter: StringParameter
  public readonly slackSigningSecretParameter: StringParameter

  constructor(scope: Construct, id: string, props: SecretsProps) {
    super(scope, id)

    // Create Slack bot OAuth token secret and parameter
    const slackBotToken = new SecretWithParameter(this, "SlackBotToken", {
      secretName: "/eps-assist/slack/bot-token",
      parameterName: "/eps-assist/slack/bot-token/parameter",
      description: "Slack Bot OAuth Token for EPS Assist",
      secretValue: JSON.stringify({token: props.slackBotToken})
    })

    // Create Slack signing secret for request verification
    const slackBotSigning = new SecretWithParameter(this, "SlackBotSigning", {
      secretName: "/eps-assist/slack/signing-secret",
      parameterName: "/eps-assist/slack/signing-secret/parameter",
      description: "Slack Signing Secret",
      secretValue: JSON.stringify({secret: props.slackSigningSecret})
    })

    // Export secrets and parameters for use by other constructs
    this.slackBotTokenSecret = slackBotToken.secret
    this.slackBotSigningSecret = slackBotSigning.secret
    this.slackBotTokenParameter = slackBotToken.parameter
    this.slackSigningSecretParameter = slackBotSigning.parameter
  }
}
