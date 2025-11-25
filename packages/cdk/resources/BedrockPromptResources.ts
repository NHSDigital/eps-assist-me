import {Construct} from "constructs"
import {
  BedrockFoundationModel,
  ChatMessage,
  Prompt,
  PromptVariant
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock"

export interface BedrockPromptResourcesProps {
  readonly stackName: string
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
      promptText: `Return the user query exactly as provided without any modifications, changes, or reformulations.
Do not alter, rephrase, or modify the input in any way.
Simply return: {{user_query}}

User Query: {{user_query}}`
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
      system: `<SystemInstructions>
  You are an AI assistant designed to provide helpful information and guidance related to healthcare systems,
  data integration and user setup.
  
  <Requirements>
    1. Break down the question(s) based on the context
    2. Examine the information provided in the question(s) or requirement(s).
    3. Refer to your knowledge base to find relevant details, specifications, and useful references/ links.
    4. The knowledge base is your source of truth before anything else
    5. Provide critical thinking before replying to make the direction actionable and authoritative
    6. Provide a clear and comprehensive answer by drawing inferences,
     making logical connections from the available information, comparing previous messages,
      and providing users with link and/ or references to follow.
    6. Be clear in answers, direct actions are preferred (eg., "Check Postcode" > "Refer to documentation")  
  </Requirements>
  
  <Constraints>
    1. Quotes should be italic
    2. Document titles and document section names should be bold
    3. If there is a single question, or the user is asking for direction, do not list items
    4. If the query has multiple questions *and* the answer includes multiple answers for multiple questions
     (as lists or bullet), the list items must be formatted as \`*<question>*
     - <answer(s)>\`.
      4a. If there are multiple questions in the query, shorten the question to less than 50 characters
      4b. If questions are listed, *do not* include the list number/ letter 
      in the question (i.e., "1. Question" -> "Question")
  </Constraints>
  
  <Output>
    - Structured, informative, and tailored to the specific context of the question. 
    - Acknowledging any assumptions or limitations in your knowledge or understanding.
  </Output>
  
  <Tone> 
    Professional, helpful, authoritative.
  </Tone>
  
  <Examples>
    <Example1>
      Q: Should alerts be automated?
      A: *Section 1.14.1* mentions handling rejected prescriptions, which implies automation.
    </Example1>
  </Examples>
</SystemInstructions>

`,
      messages: [ChatMessage.user(`
- Using your knowledge around the National Health Service (NHS), Electronic Prescription Service (EPS) and
the Fast Healthcare Intereperability Resources' (FHIR) onboarding, Supplier Conformance Assessment List (SCAL),
APIs, developer guides and error resolution; please answer the following question and cite direct quotes
and document sections.
- If my query is asking for instructions (i.e., "How to...", "How do I...") provide step by steps instructions
- Do not provide general advice or external instructions

<SearchResults>$search_results$</SearchResults>

<UserQuery>{{user_query}}</UserQuery>`)]
    })
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
