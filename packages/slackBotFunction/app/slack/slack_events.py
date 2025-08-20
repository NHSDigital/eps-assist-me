"""
Slack event processing - handles async message processing and Bedrock integration
"""

import re
import boto3
from slack_sdk import WebClient
from aws_lambda_powertools import Logger
from app.config.config import (
    KNOWLEDGEBASE_ID,
    RAG_MODEL_ID,
    AWS_REGION,
    GUARD_RAIL_ID,
    GUARD_VERSION,
    BOT_MESSAGES,
)

logger = Logger(service="slackBotFunction")


def get_bedrock_knowledgebase_response(user_query):
    """Get and return the Bedrock Knowledge Base RetrieveAndGenerate response."""
    client = boto3.client(
        service_name="bedrock-agent-runtime",
        region_name=AWS_REGION,
    )

    query_input = {
        "text": user_query,
    }

    config = {
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            "generationConfiguration": {
                "guardrailConfiguration": {
                    "guardrailId": GUARD_RAIL_ID,
                    "guardrailVersion": GUARD_VERSION,
                },
            },
            "knowledgeBaseId": KNOWLEDGEBASE_ID,
            "modelArn": RAG_MODEL_ID,
        },
    }

    response = client.retrieve_and_generate(input=query_input, retrieveAndGenerateConfiguration=config)
    logger.info("Bedrock Knowledge Base Response received", extra={"response": response})
    return response


def process_async_slack_event(slack_event_data):
    """Process Slack event asynchronously"""
    event = slack_event_data["event"]
    event_id = slack_event_data["event_id"]
    token = slack_event_data["bot_token"]

    client = WebClient(token=token)

    try:
        raw_text = event["text"]
        user_id = event["user"]
        channel = event["channel"]
        thread_ts = event.get("thread_ts", event["ts"])

        user_query = re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", raw_text).strip()

        logger.info(
            f"Processing async @mention from user {user_id}",
            extra={
                "user_query": user_query,
                "thread_ts": thread_ts,
                "event_id": event_id,
            },
        )

        if not user_query:
            client.chat_postMessage(
                channel=channel,
                text=BOT_MESSAGES["empty_query"],
                thread_ts=thread_ts,
            )
            return

        kb_response = get_bedrock_knowledgebase_response(user_query)
        response_text = kb_response["output"]["text"]

        client.chat_postMessage(channel=channel, text=response_text, thread_ts=thread_ts)

    except Exception as err:
        logger.error(f"Error processing async @mention: {err}", extra={"event_id": event_id})
        client.chat_postMessage(
            channel=channel,
            text=BOT_MESSAGES["error_response"],
            thread_ts=thread_ts,
        )
