import {Construct} from "constructs"
import {CfnPrompt} from "aws-cdk-lib/aws-bedrock"

export interface BedrockPromptProps {
  promptName: string
  promptText: string
  description: string
}

export class BedrockPrompt extends Construct {
  public readonly promptArn: string
  public readonly promptName: string

  constructor(scope: Construct, id: string, props: BedrockPromptProps) {
    super(scope, id)

    const prompt = new CfnPrompt(this, "Prompt", {
      name: props.promptName,
      description: props.description,
      variants: [
        {
          name: "default",
          templateType: "TEXT",
          templateConfiguration: {
            text: {
              text: props.promptText
            }
          }
        }
      ]
    })

    this.promptArn = prompt.attrArn
    this.promptName = prompt.name
  }
}
