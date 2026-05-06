"""Chatbot client - invokes the slackBotFunction Lambda and retrieves KB contexts.

Retrieval contexts come from Bedrock's retrieve API rather than Lambda response
citations, because direct invocation doesn't populate retrievedReferences.

Env vars:
    CHATBOT_STACK_NAME, CloudFormation stack name (e.g. epsam OR epsam-pr-42)
    AWS_REGION, AWS region (default: eu-west-2)
    _EVAL_LAMBDA_NAME, pre-resolved Lambda name (set by conftest bootstrap)
    _EVAL_KB_ID, pre-resolved KB ID (set by conftest bootstrap)
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

_NUM_RETRIEVAL_RESULTS = 5
_RETRY_CONFIG = Config(retries={"max_attempts": 8, "mode": "adaptive"})  # survive CloudFormation throttling


@lru_cache(maxsize=1)
def _resolve_lambda_name() -> str:
    """Look up the SlackBot Lambda function name from CloudFormation exports."""
    cached = os.environ.get("_EVAL_LAMBDA_NAME")
    if cached:
        return cached

    stack_name = os.environ["CHATBOT_STACK_NAME"]
    region = os.environ.get("AWS_REGION", "eu-west-2")
    export_name = f"{stack_name}:lambda:SlackBot:FunctionName"

    cf_client = boto3.client("cloudformation", region_name=region, config=_RETRY_CONFIG)

    paginator = cf_client.get_paginator("list_exports")
    for page in paginator.paginate():
        for export in page["Exports"]:
            if export["Name"] == export_name:
                logger.info("Resolved Lambda name: %s", export["Value"])
                return export["Value"]

    raise RuntimeError(f"CloudFormation export '{export_name}' not found - is '{stack_name}' deployed?")


@lru_cache(maxsize=1)
def _resolve_knowledge_base_id() -> str:
    """Look up the Knowledge Base ID from CloudFormation exports."""
    cached = os.environ.get("_EVAL_KB_ID")
    if cached:
        return cached

    stack_name = os.environ["CHATBOT_STACK_NAME"]
    region = os.environ.get("AWS_REGION", "eu-west-2")
    export_name = f"{stack_name}:bedrock:KnowledgeBase:Id"

    cf_client = boto3.client("cloudformation", region_name=region, config=_RETRY_CONFIG)

    paginator = cf_client.get_paginator("list_exports")
    for page in paginator.paginate():
        for export in page["Exports"]:
            if export["Name"] == export_name:
                logger.info("Resolved KB ID: %s", export["Value"])
                return export["Value"]

    raise RuntimeError(f"CloudFormation export '{export_name}' not found - is '{stack_name}' deployed?")


def bootstrap() -> None:
    """Resolve Lambda name and KB ID once, cache as env vars for all workers."""
    lambda_name = _resolve_lambda_name()
    kb_id = _resolve_knowledge_base_id()

    os.environ["_EVAL_LAMBDA_NAME"] = lambda_name
    os.environ["_EVAL_KB_ID"] = kb_id
    logger.info("Bootstrap complete: lambda=%s kb=%s", lambda_name, kb_id)


def _retrieve_contexts(query: str) -> list[str]:
    """Fetch knowledge base chunks for a query via Bedrock's retrieve API."""
    region = os.environ.get("AWS_REGION", "eu-west-2")
    kb_id = _resolve_knowledge_base_id()

    bedrock_client = boto3.client("bedrock-agent-runtime", region_name=region, config=_RETRY_CONFIG)
    response = bedrock_client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": _NUM_RETRIEVAL_RESULTS}},
    )

    contexts: list[str] = []
    for result in response.get("retrievalResults", []):
        text = result.get("content", {}).get("text", "")
        if text:
            contexts.append(text)

    return contexts


def get_chatbot_response(query: str) -> tuple[str, list[str]]:
    """Invoke the chatbot Lambda and return (answer, retrieved_contexts).

    The Lambda internally uses Bedrock RetrieveAndGenerate, so the answer
    already incorporates knowledge base context. We call Retrieve separately
    to obtain the raw KB chunks that DeepEval needs for retrieval metrics
    (faithfulness, relevancy, etc.), since the Lambda response does not
    expose them.
    """
    lambda_name = _resolve_lambda_name()
    region = os.environ.get("AWS_REGION", "eu-west-2")

    client = boto3.client("lambda", region_name=region, config=_RETRY_CONFIG)

    payload = {
        "invocation_type": "direct",
        "query": query,
        "session_id": None,
    }

    response = client.invoke(
        FunctionName=lambda_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    result = json.loads(response["Payload"].read())

    status_code = result.get("statusCode", 500)
    response_data = result.get("response", {})

    if status_code != 200:
        error_msg = response_data.get("error", "Unknown error")
        raise RuntimeError(f"Chatbot Lambda returned {status_code}: {error_msg}")

    answer = response_data.get("text", "")
    retrieved_contexts = _retrieve_contexts(query)
    logger.info("Response: %d chars, %d contexts", len(answer), len(retrieved_contexts))
    return answer, retrieved_contexts
