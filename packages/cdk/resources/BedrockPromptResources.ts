import {Construct} from "constructs"
import * as crypto from "crypto"
import {
  BedrockFoundationModel,
  ChatMessage,
  Prompt,
  PromptVariant
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock"
import {BedrockPromptSettings} from "./BedrockPromptSettings"
import {CfnPrompt} from "aws-cdk-lib/aws-bedrock"

export interface BedrockPromptResourcesProps {
  readonly stackName: string
  readonly settings: BedrockPromptSettings
}

export class BedrockPromptResources extends Construct {
  public readonly orchestrationReformulationPrompt: Prompt
  public readonly ragResponsePrompt: Prompt
  public readonly modelId: string

  constructor(scope: Construct, id: string, props: BedrockPromptResourcesProps) {
    super(scope, id)

    const aiModel = new BedrockFoundationModel("meta.llama3-70b-instruct-v1:0")

    // Create Prompts
    this.orchestrationReformulationPrompt = this.createPrompt(
      "OrchestrationReformulationPrompt",
      `${props.stackName}-OrchestrationReformulation`,
      "Prompt for orchestrating queries to improve RAG inference",
      aiModel,
      "",
      [props.settings.reformulationPrompt],
      props.settings.reformulationInferenceConfig
    )

    this.ragResponsePrompt = this.createPrompt(
      "RagResponsePrompt",
      `${props.stackName}-ragResponse`,
      "Prompt for generating RAG responses with knowledge base context and system instructions",
      aiModel,
      props.settings.systemPrompt.text,
      [props.settings.userPrompt],
      props.settings.ragInferenceConfig
    )

    this.modelId = aiModel.modelId
  }

  private createPrompt(
    id: string,
    promptName: string,
    description: string,
    model: BedrockFoundationModel,
    systemPromptText: string,
    messages: [ChatMessage],
    inferenceConfig: CfnPrompt.PromptModelInferenceConfigurationProperty
  ): Prompt {

    const variant = PromptVariant.chat({
      variantName: "default",
      model: model,
      promptVariables: ["prompt", "search_results"],
      system: systemPromptText,
      messages: messages
    })

    variant.inferenceConfiguration = {
      text: inferenceConfig
    }

    const hash = crypto.createHash("md5")
      .update(JSON.stringify(variant))
      .digest("hex")
      .substring(0, 6)

    return new Prompt(this, id, {
      promptName: `${promptName}-${hash}`,
      description,
      defaultVariant: variant,
      variants: [variant]
    })
  }
}
