import os
import traceback
import boto3

from app.core.config import get_logger
from app.services.bedrock import invoke_model
from .prompt_loader import load_prompt
from .exceptions import ConfigurationError
from mypy_boto3_bedrock_runtime.client import BedrockRuntimeClient

logger = get_logger()


def reformulate_query(user_query: str) -> str:
    """
    Reformulate user query using Amazon Nova Lite for better RAG retrieval.

    Loads prompt template from Bedrock Prompt Management, formats it with the user's
    query, and uses Nova Lite to generate a reformulated version optimized for vector search.
    """
    try:
        client: BedrockRuntimeClient = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
        model_id = os.environ["QUERY_REFORMULATION_MODEL_ID"]

        # Load prompt template from Bedrock Prompt Management
        prompt_name = os.environ.get("QUERY_REFORMULATION_PROMPT_NAME")
        prompt_version = os.environ.get("QUERY_REFORMULATION_PROMPT_VERSION", "DRAFT")

        if not prompt_name:
            raise ConfigurationError("QUERY_REFORMULATION_PROMPT_NAME environment variable not set")

        # Load prompt with specified version (DRAFT by default)
        prompt_template = load_prompt(prompt_name, prompt_version)

        logger.info(
            "Prompt loaded successfully from Bedrock",
            extra={"prompt_name": prompt_name, "version_used": prompt_version},
        )

        # Format the prompt with the user query (using double braces from Bedrock template)
        # pyrefly: ignore [missing-attribute]
        prompt = prompt_template.get("prompt_text").replace("{{user_query}}", user_query)
        result = invoke_model(
            prompt=prompt,
            model_id=model_id,
            client=client,
            inference_config=prompt_template.get("inference_config", {}),
        )

        reformulated_query = result["content"][0]["text"].strip()

        logger.info(
            "Query reformulated successfully using Bedrock prompt",
            extra={
                "original_query": user_query,
                "reformulated_query": reformulated_query,
                "prompt_version_used": prompt_version,
                "prompt_source": "bedrock_prompt_management",
            },
        )

        return reformulated_query

    except Exception as e:
        logger.error(
            f"Failed to reformulate query using Bedrock prompts: {e}",
            extra={
                "original_query": user_query,
                "prompt_name": os.environ.get("QUERY_REFORMULATION_PROMPT_NAME"),
                "prompt_version": os.environ.get("QUERY_REFORMULATION_PROMPT_VERSION", "auto"),
                "error_type": type(e).__name__,
                "error": traceback.format_exc(),
            },
        )

        # Graceful degradation - return original query but alert on infrastructure issue
        logger.error(
            "Query reformulation degraded: Bedrock Prompt Management unavailable",
            extra={
                "service_status": "degraded",
                "fallback_action": "using_original_query",
                "requires_attention": True,
                "impact": "reduced_rag_quality",
            },
        )

        return user_query  # Minimal fallback - just return original query
