import {Construct} from "constructs"
import {Role} from "aws-cdk-lib/aws-iam"
import {Bucket} from "aws-cdk-lib/aws-s3"
import {bedrock} from "@cdklabs/generative-ai-cdk-constructs"
import {
  ContentFilterType,
  ContentFilterStrength,
  ManagedWordFilterType,
  PIIType,
  GuardrailAction
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock/guardrails/guardrail-filters"

export interface VectorKnowledgeBaseProps {
  kbName: string
  embeddingsModel: bedrock.BedrockFoundationModel
  docsBucket: Bucket
  bedrockExecutionRole: Role
}

export class VectorKnowledgeBaseResources extends Construct {
  public readonly knowledgeBase: bedrock.VectorKnowledgeBase
  public readonly guardrail: bedrock.Guardrail

  constructor(scope: Construct, id: string, props: VectorKnowledgeBaseProps) {
    super(scope, id)

    this.guardrail = new bedrock.Guardrail(this, "Guardrail", {
      name: "eps-assist-guardrail",
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
        {type: PIIType.General.EMAIL, action: GuardrailAction.ANONYMIZE},
        {type: PIIType.General.PHONE, action: GuardrailAction.ANONYMIZE},
        {type: PIIType.General.NAME, action: GuardrailAction.ANONYMIZE},
        {type: PIIType.Finance.CREDIT_DEBIT_CARD_NUMBER, action: GuardrailAction.BLOCK}
      ],
      managedWordListFilters: [
        {type: ManagedWordFilterType.PROFANITY}
      ]
    })

    // Main construct - let it create its own default OpenSearch collection
    this.knowledgeBase = new bedrock.VectorKnowledgeBase(this, "VectorKB", {
      name: props.kbName,
      description: "Knowledge base for EPS Assist Me Slackbot",
      embeddingsModel: props.embeddingsModel,
      existingRole: props.bedrockExecutionRole
    })

    // Add S3 data source to knowledge base
    this.knowledgeBase.addS3DataSource({
      bucket: props.docsBucket
    })
  }
}
