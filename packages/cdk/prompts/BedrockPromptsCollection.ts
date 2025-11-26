import * as fs from "fs"
import {ChatMessage} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock"
import {Construct} from "constructs"

export type BedrockPromptCollectionType = "systemPrompt" | "userPrompt" | "reformulationPrompt"

export interface BedrockPromptCollectionProps {
  readonly systemPromptVersion: string | undefined
  readonly userPromptVersion: string | undefined
  readonly reformulationPromptVersion: string | undefined
}

/** BedrockPromptCollection is responsible for loading and providing
 * the prompt texts for system, user, and reformulation prompts.
 */
export class BedrockPromptCollection extends Construct {
  public readonly systemPrompt: ChatMessage
  public readonly userPrompt: ChatMessage
  public readonly reformulationPrompt: ChatMessage

  /**
   * @param scope The Construct scope
   * @param id The Construct ID
   * @param props BedrockPromptCollectionProps containing optional version info for each prompt
   */
  constructor(scope: Construct, id: string, props: BedrockPromptCollectionProps) {
    super(scope, id)

    const systemPromptData = this.getVersionedPrompt("systemPrompt", props.systemPromptVersion)
    this.systemPrompt = ChatMessage.assistant(systemPromptData.text)

    const userPromptData = this.getVersionedPrompt("userPrompt", props.userPromptVersion)
    this.userPrompt = ChatMessage.user(userPromptData.text)

    const reformulationPrompt = this.getVersionedPrompt("reformulationPrompt", props.reformulationPromptVersion)
    this.reformulationPrompt = ChatMessage.user(reformulationPrompt.text)
  }

  /** Get the latest prompt text from files in the specified directory.
   * If a version is provided, it retrieves that specific version.
   * Otherwise, it retrieves the latest version based on file naming.
   *
   * @param type The type of prompt (systemPrompt, userPrompt, reformulationPrompt)
   * @param version Optional specific version to retrieve
   * @param directory Directory where prompt files are stored
   * @returns An object containing the prompt text and filename
   */
  private getVersionedPrompt(type: BedrockPromptCollectionType, version: string | undefined = undefined)
  : { text: string; filename: string } {
    // Read all files in the folder
    const files = fs.readdirSync(".").filter(f => f.startsWith(`${type}_v`) && f.endsWith(".txt"))

    if (files.length === 0) {
      throw new Error("No variant files found in the folder.")
    }

    // Check if a specific version is requested
    if (version) {
      const matchedFile = files.find(f => f.includes(`_v${version}`))
      if (!matchedFile) {
        throw new Error(`No variant file found for version ${version}`)
      }

      const text = fs.readFileSync(matchedFile, "utf-8")
      return {text, filename: matchedFile}
    }

    // Sort by version number
    files.sort((a, b) => {
      const versionA = parseInt(a.split("_v")[1].split(".")[0], 10)
      const versionB = parseInt(b.split("_v")[1].split(".")[0], 10)
      return versionA - versionB
    })

    const latestFile = files[files.length - 1]

    const text = fs.readFileSync(latestFile, "utf-8")

    return {text, filename: latestFile}
  }
}
