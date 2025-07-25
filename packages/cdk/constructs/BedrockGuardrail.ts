import {Construct} from "constructs"
import {CfnGuardrail, CfnGuardrailVersion} from "aws-cdk-lib/aws-bedrock"

export interface BedrockGuardrailProps {
  name: string
  description: string
}

export class BedrockGuardrail extends Construct {
  public readonly guardrail: CfnGuardrail
  public readonly guardrailVersion: CfnGuardrailVersion
  public readonly guardrailId: string
  public readonly guardrailVersionId: string

  constructor(scope: Construct, id: string, props: BedrockGuardrailProps) {
    super(scope, id)

    this.guardrail = new CfnGuardrail(this, "Guardrail", {
      name: props.name,
      description: props.description,
      blockedInputMessaging: "Your input was blocked.",
      blockedOutputsMessaging: "Your output was blocked.",
      contentPolicyConfig: {
        filtersConfig: [
          {type: "SEXUAL", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "VIOLENCE", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "HATE", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "INSULTS", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "MISCONDUCT", inputStrength: "HIGH", outputStrength: "HIGH"},
          {type: "PROMPT_ATTACK", inputStrength: "HIGH", outputStrength: "NONE"}
        ]
      },
      sensitiveInformationPolicyConfig: {
        piiEntitiesConfig: [
          {type: "EMAIL", action: "ANONYMIZE"},
          {type: "PHONE", action: "ANONYMIZE"},
          {type: "NAME", action: "ANONYMIZE"},
          {type: "CREDIT_DEBIT_CARD_NUMBER", action: "BLOCK"}
        ]
      },
      wordPolicyConfig: {
        managedWordListsConfig: [{type: "PROFANITY"}]
      }
    })

    this.guardrailVersion = new CfnGuardrailVersion(this, "GuardrailVersion", {
      guardrailIdentifier: this.guardrail.attrGuardrailId,
      description: "v1.0"
    })

    this.guardrailId = this.guardrail.attrGuardrailId
    this.guardrailVersionId = this.guardrailVersion.attrVersion
  }
}
