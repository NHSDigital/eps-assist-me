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
from app.services.query_reformulator import reformulate_query

logger = Logger(service="slackBotFunction")


def get_bedrock_knowledgebase_response(user_query):
    """
    Query Amazon Bedrock Knowledge Base using RAG (Retrieval-Augmented Generation)

    This function retrieves relevant documents from the knowledge base and generates
    a response using the configured LLM model with guardrails for safety.
    """
    client = boto3.client(
        service_name="bedrock-agent-runtime",
        region_name=AWS_REGION,
    )

    # Structure the user's query for Bedrock
    query_input = {
        "text": user_query,
    }

    # Configure knowledge base with model and safety guardrails
    config = {
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            "generationConfiguration": {
                "guardrailConfiguration": {
                    "guardrailId": GUARD_RAIL_ID,  # Content filtering and safety rules
                    "guardrailVersion": GUARD_VERSION,
                },
            },
            "knowledgeBaseId": KNOWLEDGEBASE_ID,  # Vector database with EPS documents
            "modelArn": RAG_MODEL_ID,  # LLM model for text generation
        },
    }

    # Execute RAG: retrieve relevant docs + generate response
    response = client.retrieve_and_generate(input=query_input, retrieveAndGenerateConfiguration=config)
    logger.info("Bedrock Knowledge Base Response received", extra={"response": response})
    return response


def process_async_slack_event(slack_event_data):
    """
    Process Slack events asynchronously after initial acknowledgment

    This function handles the actual AI processing that takes longer than Slack's
    3-second timeout. It extracts the user query, calls Bedrock, and posts the response.
    """
    event = slack_event_data["event"]
    event_id = slack_event_data["event_id"]
    token = slack_event_data["bot_token"]

    client = WebClient(token=token)

    try:
        # Extract message details from Slack event
        raw_text = event["text"]
        user_id = event["user"]
        channel = event["channel"]
        # Use thread_ts for threaded replies, fallback to message timestamp
        thread_ts = event.get("thread_ts", event["ts"])

        # Remove bot mention tags from message text (e.g., "<@U123456789>")
        user_query = re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", raw_text).strip()

        logger.info(
            f"Processing async @mention from user {user_id}",
            extra={
                "user_query": user_query,
                "thread_ts": thread_ts,
                "event_id": event_id,
            },
        )

        # Handle empty queries after removing bot mentions
        if not user_query:
            client.chat_postMessage(
                channel=channel,
                text=BOT_MESSAGES["empty_query"],
                thread_ts=thread_ts,  # Reply in thread to keep conversation organized
            )
            return

        # Reformulate query for better RAG retrieval
        reformulated_query = reformulate_query(user_query)
        logger.info("Query reformulated", extra={"original": user_query, "reformulated": reformulated_query})

        # Query the knowledge base with reformulated query
        kb_response = get_bedrock_knowledgebase_response(reformulated_query)
        response_text = kb_response["output"]["text"]

        # Post the AI response back to Slack in the same thread
        client.chat_postMessage(channel=channel, text=response_text, thread_ts=thread_ts)

    except Exception as err:
        logger.error(f"Error processing async @mention: {err}", extra={"event_id": event_id})
        # Send user-friendly error message instead of exposing technical details
        client.chat_postMessage(
            channel=channel,
            text=BOT_MESSAGES["error_response"],
            thread_ts=thread_ts,
        )
