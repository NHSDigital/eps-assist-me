# flake8: noqa: E501
import os
import json
import boto3
from aws_lambda_powertools import Logger

logger = Logger(service="queryReformulator")


def reformulate_query(user_query: str) -> str:
    """
    Reformulate user query using Claude Haiku for better RAG retrieval.
    """
    try:
        client = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
        model_id = os.environ["QUERY_REFORMULATION_MODEL_ID"]

        prompt = f"""You are a query reformulation assistant for the NHS EPS (Electronic Prescription Service) API documentation system.

    Your task is to reformulate user queries to improve retrieval from a knowledge base containing FHIR NHS EPS API documentation, onboarding guides, and technical specifications.

    Guidelines:
    - Expand abbreviations (EPS = Electronic Prescription Service, FHIR = Fast Healthcare Interoperability Resources)
    - Add relevant technical context (API, prescription, dispensing, healthcare)
    - Convert casual language to technical terminology
    - Include synonyms for better matching
    - Keep the core intent intact
    - Focus on NHS, healthcare, prescription, and API-related terms
    - Maintain question format with proper punctuation

    User Query: {user_query}

    Return only the reformulated query as a complete question:"""

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
