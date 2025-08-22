import os
import json
import boto3
from aws_lambda_powertools import Logger
from .prompt_loader import load_prompt

logger = Logger(service="queryReformulator")


def reformulate_query(user_query: str) -> str:
    """
    Reformulate user query using Claude Haiku for better RAG retrieval.
    """
    try:
        client = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
        model_id = os.environ["QUERY_REFORMULATION_MODEL_ID"]

        prompt_name = os.environ.get("QUERY_REFORMULATION_PROMPT_NAME", "query-reformulation")
        prompt_template = load_prompt(prompt_name)
        prompt = prompt_template.format(user_query=user_query)

        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}],
                }
            ),
        )

        result = json.loads(response["body"].read())
        reformulated_query = result["content"][0]["text"].strip()

        logger.info(
            "Query reformulated", extra={"original_query": user_query, "reformulated_query": reformulated_query}
        )

        return reformulated_query

    except Exception as e:
        logger.error(f"Error reformulating query: {e}", extra={"original_query": user_query})
        return user_query  # Fallback to original query
