import json
from typing import Any
import boto3
from mypy_boto3_bedrock_agent_runtime import AgentsforBedrockRuntimeClient
from mypy_boto3_bedrock_runtime.client import BedrockRuntimeClient
from mypy_boto3_bedrock_agent_runtime.type_defs import RetrieveAndGenerateResponseTypeDef

from app.core.config import get_retrieve_generate_config, get_logger
from app.services.prompt_loader import load_prompt


logger = get_logger()


def query_bedrock(user_query: str, session_id: str = None) -> RetrieveAndGenerateResponseTypeDef:
    """
    Query Amazon Bedrock Knowledge Base using RAG (Retrieval-Augmented Generation)

    This function retrieves relevant documents from the knowledge base and generates
    a response using the configured LLM model with guardrails for safety.
    """

    config = get_retrieve_generate_config()
    prompt_template = load_prompt(config.RAG_RESPONSE_PROMPT_NAME, config.RAG_RESPONSE_PROMPT_VERSION)
    inference_config = prompt_template.get("inference_config")

    if not inference_config:
        default_values = {"temperature": 0, "maxTokens": 512, "topP": 1}
        inference_config = default_values
        logger.warning(
            "No inference configuration found in prompt template; using default values",
            extra={"prompt_name": config.RAG_RESPONSE_PROMPT_NAME, "default_inference_config": default_values},
        )

    client: AgentsforBedrockRuntimeClient = boto3.client(
        service_name="bedrock-agent-runtime",
        region_name=config.AWS_REGION,
    )
    request_params = {
        "input": {"text": user_query},
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": config.KNOWLEDGEBASE_ID,
                "modelArn": config.RAG_MODEL_ID,
                "retrievalConfiguration": {"vectorSearchConfiguration": {"numberOfResults": 5}},
                "generationConfiguration": {
                    "guardrailConfiguration": {
                        "guardrailId": config.GUARD_RAIL_ID,
                        "guardrailVersion": config.GUARD_VERSION,
                    },
                    "inferenceConfig": {
                        "textInferenceConfig": {
                            **inference_config,
                            "stopSequences": [
                                "Human:",
                            ],
                        }
                    },
                },
                "orchestrationConfiguration": {
                    "inferenceConfig": {
                        "textInferenceConfig": {
                            **inference_config,
                            "stopSequences": [
                                "Human:",
                            ],
                        }
                    },
                },
            },
        },
    }

    if prompt_template:
        request_params["retrieveAndGenerateConfiguration"]["knowledgeBaseConfiguration"]["generationConfiguration"][
            "promptTemplate"
        ] = {"textPromptTemplate": prompt_template.get("prompt_text")}
        logger.info(
            "Using prompt template for RAG response generation", extra={"prompt_name": config.RAG_RESPONSE_PROMPT_NAME}
        )

    # Include session ID for conversation continuity across messages
    if session_id:
        request_params["sessionId"] = session_id
        logger.info("Using existing session", extra={"session_id": session_id})
    else:
        logger.info("Starting new conversation")

    response = client.retrieve_and_generate(**request_params)
    logger.info(
        "Got Bedrock response",
        extra={"session_id": response.get("sessionId")},
    )
    return response


def invoke_model(prompt: str, model_id: str, client: BedrockRuntimeClient, inference_config: dict) -> dict[str, Any]:
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "temperature": inference_config["temperature"],
                "top_p": inference_config["topP"],
                "top_k": 50,
                "max_tokens": inference_config["maxTokens"],
                "messages": [{"role": "user", "content": prompt}],
            }
        ),
    )

    result = json.loads(response["body"].read())
    return result
