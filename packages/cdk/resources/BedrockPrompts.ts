import {Construct} from "constructs"
import {BedrockPrompt} from "../constructs/BedrockPrompt"

export interface BedrockPromptsProps {
  readonly stackName: string
}

export class BedrockPrompts extends Construct {
  public readonly queryReformulationPrompt: BedrockPrompt

  constructor(scope: Construct, id: string, props: BedrockPromptsProps) {
    super(scope, id)

    this.queryReformulationPrompt = new BedrockPrompt(this, "QueryReformulationPrompt", {
      promptName: `${props.stackName}-queryReformulation`,
      promptText: "PLACEHOLDER",
      description: "Prompt for reformulating user queries to improve RAG retrieval"
    })
  }
}
