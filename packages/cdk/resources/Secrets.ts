import {Construct} from "constructs"
import {StringParameter} from "aws-cdk-lib/aws-ssm"
import {Secret} from "aws-cdk-lib/aws-secretsmanager"
import {SecretWithParameter} from "../constructs/SecretWithParameter"
import {Key} from "aws-cdk-lib/aws-kms"

export interface SecretsProps {
  readonly stackName: string
  readonly slackBotToken: string
  readonly slackSigningSecret: string
}

export class Secrets extends Construct {
  public readonly slackBotTokenSecret: Secret
  public readonly slackBotSigningSecret: Secret
  public readonly slackBotTokenParameter: StringParameter
  public readonly slackSigningSecretParameter: StringParameter
  public readonly secretsKmsKey: Key

  constructor(scope: Construct, id: string, props: SecretsProps) {
    super(scope, id)

    this.secretsKmsKey = new Key(this, "SecretsKmsKey", {
      alias: `${props.stackName}-secrets-key`,
      description: "KMS Key for EPS Assist Secrets",
      enableKeyRotation: true
    })

    // Create Slack bot OAuth token secret and parameter
    const slackBotToken = new SecretWithParameter(this, "SlackBotToken", {
      secretName: `/${props.stackName}/bot-token`,
      parameterName: `/${props.stackName}/bot-token/parameter`,
      description: "Slack Bot OAuth Token for EPS Assist",
      secretValue: JSON.stringify({token: props.slackBotToken}),
      encryptionKey: this.secretsKmsKey
    })

    // Create Slack signing secret for request verification
    const slackBotSigning = new SecretWithParameter(this, "SlackBotSigning", {
      secretName: `/${props.stackName}/signing-secret`,
      parameterName: `/${props.stackName}/signing-secret/parameter`,
      description: "Slack Signing Secret",
      secretValue: JSON.stringify({secret: props.slackSigningSecret}),
      encryptionKey: this.secretsKmsKey
    })

    // Export secrets and parameters for use by other constructs
    this.slackBotTokenSecret = slackBotToken.secret
    this.slackBotSigningSecret = slackBotSigning.secret
    this.slackBotTokenParameter = slackBotToken.parameter
    this.slackSigningSecretParameter = slackBotSigning.parameter
  }
}
