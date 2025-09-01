import {Construct} from "constructs"
import {BedrockPrompt} from "../constructs/BedrockPrompt"

export interface BedrockPromptResourcesProps {
  readonly stackName: string
}

export class BedrockPromptResources extends Construct {
  public readonly queryReformulationPrompt: BedrockPrompt

  constructor(scope: Construct, id: string, props: BedrockPromptResourcesProps) {
    super(scope, id)

    this.queryReformulationPrompt = new BedrockPrompt(this, "QueryReformulationPrompt", {
      promptName: `${props.stackName}-queryReformulation`,
      promptText: `Return the user query exactly as provided without any modifications, changes, or reformulations.
Do not alter, rephrase, or modify the input in any way.
Simply return: {{user_query}}

User Query: {{user_query}}`,
      description: "Prompt for reformulating user queries to improve RAG retrieval"
    })
  }
}
