import os
import json
import boto3
from aws_lambda_powertools import Logger

logger = Logger(service="queryReformulator")


def reformulate_query(user_query: str) -> str:
    """
    Reformulate user query using Bedrock Prompt Management for better RAG retrieval.
    """
    try:
        client = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
        prompt_arn = os.environ["QUERY_REFORMULATION_PROMPT_ARN"]

        response = client.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 200,
                    "prompt": prompt_arn,
                    "variables": {"query": user_query},
                }
            ),
        )

        result = json.loads(response["body"].read())
        reformulated_query = result["content"][0]["text"].strip()

        logger.info(
            "Query reformulated",
            extra={
                "original_query": user_query,
                "reformulated_query": reformulated_query,
            },
        )

        return reformulated_query

    except Exception as e:
        logger.error(
            f"Error reformulating query: {e}",
            extra={"original_query": user_query, "prompt_arn": os.environ.get("QUERY_REFORMULATION_PROMPT_ARN")},
        )
        return user_query  # Fallback to original query
