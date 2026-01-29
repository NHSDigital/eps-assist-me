import {Construct} from "constructs"
import {
  ContentFilterStrength,
  ContentFilterType,
  Guardrail,
  GuardrailAction,
  ManagedWordFilterType,
  PIIType
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock"

export interface GuardRailResourcesProps {
  readonly stackName: string
}

export class GuardRailResources extends Construct {
  public readonly guardrail: Guardrail

  constructor(scope: Construct, id: string, props: GuardRailResourcesProps) {
    super(scope, id)

    const guardrail = new Guardrail(this, "bedrockGuardrails", {
      name: `${props.stackName}-guardrail`,
      description: "Guardrail for EPS Assist Me Slackbot",
      blockedInputMessaging: "Your input was blocked.",
      blockedOutputsMessaging: "Your output was blocked.",
      contentFilters: [
        {
          type: ContentFilterType.SEXUAL,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.VIOLENCE,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.HATE,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.INSULTS,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.MISCONDUCT,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.HIGH
        },
        {
          type: ContentFilterType.PROMPT_ATTACK,
          inputStrength: ContentFilterStrength.HIGH,
          outputStrength: ContentFilterStrength.NONE
        }
      ],
      piiFilters: [
        {
          type: PIIType.General.EMAIL,
          action: GuardrailAction.ANONYMIZE
        },
        {
          type: PIIType.General.PHONE,
          action: GuardrailAction.ANONYMIZE
        },
        {
          type: PIIType.General.NAME,
          action: GuardrailAction.ANONYMIZE
        },
        {
          type: PIIType.Finance.CREDIT_DEBIT_CARD_NUMBER,
          action: GuardrailAction.BLOCK
        },
        {
          type: PIIType.UKSpecific.UK_NATIONAL_HEALTH_SERVICE_NUMBER,
          action: GuardrailAction.ANONYMIZE
        }
      ],
      managedWordListFilters: [
        {type: ManagedWordFilterType.PROFANITY}
      ]
    })

    this.guardrail = guardrail
  }
}
