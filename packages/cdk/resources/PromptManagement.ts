import {Construct} from "constructs"
import {CfnPrompt} from "aws-cdk-lib/aws-bedrock"

export interface PromptManagementProps {
  readonly stackName: string
}

export class PromptManagement extends Construct {
  public readonly queryReformulationPrompt: CfnPrompt

  constructor(scope: Construct, id: string, props: PromptManagementProps) {
    super(scope, id)

    this.queryReformulationPrompt = new CfnPrompt(this, "QueryReformulationPrompt", {
      name: `${props.stackName}-query-reformulation`,
      description: "Reformulates user queries for better RAG retrieval",
      defaultVariant: "default",
      variants: [{
        name: "default",
        templateType: "TEXT",
        templateConfiguration: {
          text: {
            text: `You are a query reformulation assistant for the NHS EPS (Electronic Prescription Service) API ` +
              `documentation system.

Your task is to reformulate user queries to improve retrieval from a knowledge base containing FHIR NHS EPS API 
documentation, onboarding guides, and technical specifications.

Guidelines:
- Expand abbreviations (EPS = Electronic Prescription Service, FHIR = Fast Healthcare Interoperability Resources)
- Add relevant technical context (API, prescription, dispensing, healthcare)
- Convert casual language to technical terminology
- Include synonyms for better matching
- Keep the core intent intact
- Focus on NHS, healthcare, prescription, and API-related terms

User Query: {{query}}

Reformulated Query:`
          }
        },
        modelId: "anthropic.claude-3-haiku-20240307-v1:0"
      }]
    })
  }
}
