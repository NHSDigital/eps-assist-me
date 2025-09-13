import os
import json
import traceback
import boto3
from .prompt_loader import load_prompt
from .exceptions import ConfigurationError


def reformulate_query(logger, user_query: str) -> str:
    """
    Reformulate user query using Claude Haiku for better RAG retrieval.

    Loads prompt template from Bedrock Prompt Management, formats it with the user's
    query, and uses Claude to generate a reformulated version optimized for vector search.
    """
    try:
        client = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
        model_id = os.environ["QUERY_REFORMULATION_MODEL_ID"]

        # Load prompt template from Bedrock Prompt Management
        prompt_name = os.environ.get("QUERY_REFORMULATION_PROMPT_NAME")
        prompt_version = os.environ.get("QUERY_REFORMULATION_PROMPT_VERSION", "DRAFT")

        if not prompt_name:
            raise ConfigurationError("QUERY_REFORMULATION_PROMPT_NAME environment variable not set")

        # Load prompt with specified version (DRAFT by default)
        prompt_template = load_prompt(logger, prompt_name, prompt_version)

        logger.info(
            "Prompt loaded successfully from Bedrock",
            extra={"prompt_name": prompt_name, "version_used": prompt_version},
        )

        # Format the prompt with the user query (using double braces from Bedrock template)
        prompt = prompt_template.replace("{{user_query}}", user_query)

        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "top_k": 50,
                    "max_tokens": 150,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ),
        )

        result = json.loads(response["body"].read())
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
