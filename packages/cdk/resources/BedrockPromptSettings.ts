import * as fs from "fs"
import {ChatMessage} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock"
import {Construct} from "constructs"
import {CfnPrompt} from "aws-cdk-lib/aws-bedrock"

export type BedrockPromptSettingsType = "system" | "user" | "reformulation"

/** BedrockPromptSettings is responsible for loading and providing
 * the system, user, and reformulation prompts along with their
 * inference configurations.
 */
export class BedrockPromptSettings extends Construct {
  public readonly systemPrompt: ChatMessage
  public readonly userPrompt: ChatMessage
  public readonly reformulationPrompt: ChatMessage
  public readonly ragInferenceConfig: CfnPrompt.PromptModelInferenceConfigurationProperty
  public readonly reformulationInferenceConfig: CfnPrompt.PromptModelInferenceConfigurationProperty

  /**
   * @param scope The Construct scope
   * @param id The Construct ID
   * @param props BedrockPromptSettingsProps containing optional version info for each prompt
   */
  constructor(scope: Construct, id: string) {
    super(scope, id)

    const systemPromptData = this.getTypedPrompt("system")
    this.systemPrompt = ChatMessage.assistant(systemPromptData.text)

    const userPromptData = this.getTypedPrompt("user")
    this.userPrompt = ChatMessage.user(userPromptData.text)

    const reformulationPrompt = this.getTypedPrompt("reformulation")
    this.reformulationPrompt = ChatMessage.user(reformulationPrompt.text)

    this.ragInferenceConfig = {
      temperature: 0,
      topP: 0.1,
      maxTokens: 1024,
      stopSequences: [
        "Human:"
      ]
    }

    this.reformulationInferenceConfig = {
      temperature: 0.5,
      topP: 0.9,
      maxTokens: 512,
      stopSequences: [
        "Human:"
      ]
    }
  }

  /** Get the latest prompt text from files in the specified directory.
   * If a version is provided, it retrieves that specific version.
   * Otherwise, it retrieves the latest version based on file naming.
   *
   * @param type The type of prompt (system, user, reformulation)
   * @returns An object containing the prompt text and filename
   */
  private getTypedPrompt(type: BedrockPromptSettingsType)
  : { text: string; filename: string } {
    // Read all files in the folder)
    const path = __dirname + "/../prompts"
    const files = fs
      .readdirSync(path)

    if (files.length === 0) {
      throw new Error("No variant files found in the folder.")
    }

    const file = files.find(file => file.startsWith(`${type}Prompt`))!

    if (!file) {
      throw new Error(`No prompt file found for type: ${type}`)
    }

    const text = fs.readFileSync(`${path}/${file}`, "utf-8")

    return {text, filename: file}
  }
}
