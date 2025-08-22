import {Construct} from "constructs"
import {BedrockPrompt} from "../constructs/BedrockPrompt"

export class BedrockPrompts extends Construct {
  public readonly queryReformulationPrompt: BedrockPrompt

  constructor(scope: Construct, id: string) {
    super(scope, id)

    this.queryReformulationPrompt = new BedrockPrompt(this, "QueryReformulationPrompt", {
      promptName: "query-reformulation",
      promptText: "PLACEHOLDER - Update this prompt text via AWS Console",
      description: "Prompt for reformulating user queries to improve RAG retrieval - UPDATE VIA CONSOLE"
    })
  }
}
