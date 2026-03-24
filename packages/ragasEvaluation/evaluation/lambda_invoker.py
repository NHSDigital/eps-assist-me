"""
Lambda invoker for Ragas evaluation.

Calls the deployed Slack Bot Lambda via direct invocation (bypasses Slack)
and returns the AI response with citations for evaluation.
"""

import json
import logging

import boto3

from evaluation.config import LAMBDA_FUNCTION_NAME, AWS_REGION

logger = logging.getLogger(__name__)


def invoke_bot(query: str, session_id: str | None = None) -> dict:
    """
    Invoke the deployed EPS Assist Me Lambda with a direct query.

    Args:
        query: The user question to send to the bot.
        session_id: Optional session ID for conversation continuity.

    Returns:
        dict with keys: text, session_id, citations
    """
    client = boto3.client("lambda", region_name=AWS_REGION)

    payload = {
        "invocation_type": "direct",
        "query": query,
    }
    if session_id:
        payload["session_id"] = session_id

    logger.info("Invoking Lambda %s with query: %s", LAMBDA_FUNCTION_NAME, query[:80])

    response = client.invoke(
        FunctionName=LAMBDA_FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    response_payload = json.loads(response["Payload"].read())

    if response_payload.get("statusCode") != 200:
        raise RuntimeError(f"Lambda invocation failed: {response_payload}")

    data = response_payload["response"]
    logger.info("Got response (session=%s, %d citations)", data.get("session_id"), len(data.get("citations", [])))

    return {
        "text": data["text"],
        "session_id": data.get("session_id"),
        "citations": data.get("citations", []),
    }
