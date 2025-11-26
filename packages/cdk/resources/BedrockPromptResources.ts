import {Construct} from "constructs"
import {
  BedrockFoundationModel,
  Prompt,
  PromptVariant
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock"
import {BedrockPromptSettings} from "./BedrockPromptSettings"

export interface BedrockPromptResourcesProps {
  readonly stackName: string
  readonly settings: BedrockPromptSettings
}

export class BedrockPromptResources extends Construct {
  public readonly queryReformulationPrompt: Prompt
  public readonly ragResponsePrompt: Prompt

  constructor(scope: Construct, id: string, props: BedrockPromptResourcesProps) {
    super(scope, id)

    const claudeHaikuModel = BedrockFoundationModel.ANTHROPIC_CLAUDE_HAIKU_V1_0
    const claudeSonnetModel = BedrockFoundationModel.ANTHROPIC_CLAUDE_SONNET_V1_0

    const queryReformulationPromptVariant = PromptVariant.text({
      variantName: "default",
      model: claudeHaikuModel,
      promptVariables: ["topic"],
      promptText: props.settings.reformulationPrompt.text
    })

    const queryReformulationPrompt = new Prompt(this, "QueryReformulationPrompt", {
      promptName: `${props.stackName}-queryReformulation`,
      description: "Prompt for reformulating user queries to improve RAG retrieval",
      defaultVariant: queryReformulationPromptVariant,
      variants: [queryReformulationPromptVariant]
    })

    const ragResponsePromptVariant = PromptVariant.chat({
      variantName: "default",
      model: claudeSonnetModel,
      promptVariables: ["query", "search_results"],
      system: props.settings.systemPrompt.text,
      messages: [props.settings.userPrompt]
    })

    ragResponsePromptVariant.inferenceConfiguration = {
      text: props.settings.inferenceConfig
    }

    const ragPrompt = new Prompt(this, "ragResponsePrompt", {
      promptName: `${props.stackName}-ragResponse`,
      description: "Prompt for generating RAG responses with knowledge base context and system instructions",
      defaultVariant: ragResponsePromptVariant,
      variants: [ragResponsePromptVariant]
    })

    this.queryReformulationPrompt = queryReformulationPrompt
    this.ragResponsePrompt = ragPrompt
  }
}
