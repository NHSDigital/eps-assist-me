import {Construct} from "constructs"
import {BedrockFoundationModel, Prompt, PromptVariant} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock"

export interface BedrockPromptResourcesProps {
  readonly stackName: string
}

export class BedrockPromptResources extends Construct {
  public readonly queryReformulationPrompt: Prompt

  constructor(scope: Construct, id: string, props: BedrockPromptResourcesProps) {
    super(scope, id)

    const claudeModel = BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_HAIKU_V1_0
    const promptVariant = PromptVariant.text({
      variantName: "default",
      model: claudeModel,
      promptVariables: ["topic"],
      promptText: `Return the user query exactly as provided without any modifications, changes, or reformulations.
Do not alter, rephrase, or modify the input in any way.
Simply return: {{user_query}}

User Query: {{user_query}}`
    })
    const queryReformulationPrompt = new Prompt(this, "QueryReformulationPrompt", {
      promptName: `${props.stackName}-queryReformulation`,
      description: "Prompt for reformulating user queries to improve RAG retrieval",
      defaultVariant: promptVariant,
      variants: [promptVariant]
    })

    this.queryReformulationPrompt = queryReformulationPrompt
  }
}
