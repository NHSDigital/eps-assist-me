"""
Slack event processing
Handles conversation memory, Bedrock queries, and responding back to Slack
"""

import re
import time
import traceback
import boto3
from slack_sdk import WebClient
from app.core.config import (
    get_bot_messages,
    get_guardrail_config,
    get_slack_bot_state_table,
    get_logger,
)
from app.services.query_reformulator import reformulate_query

logger = get_logger()


def process_async_slack_event(slack_event_data):
    """
    Process Slack events asynchronously after initial acknowledgment

    This function handles the actual AI processing that takes longer than Slack's
    3-second timeout. It extracts the user query, calls Bedrock, and posts the response.
    """
    event = slack_event_data["event"]
    event_id = slack_event_data["event_id"]
    token = slack_event_data["bot_token"]
    BOT_MESSAGES = get_bot_messages()

    client = WebClient(token=token)

    try:
        raw_text = event["text"]
        user_id = event["user"]
        channel = event["channel"]
        thread_ts = event.get("thread_ts", event["ts"])

        # figure out if this is a DM or channel thread
        if event.get("channel_type") == "im":
            conversation_key = f"dm#{channel}"
            context_type = "DM"
        else:
            conversation_key = f"thread#{channel}#{thread_ts}"
            context_type = "thread"

        # clean up the user's message
        user_query = re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", raw_text).strip()

        logger.info(
            f"Processing {context_type} message from user {user_id}",
            extra={"user_query": user_query, "conversation_key": conversation_key, "event_id": event_id},
        )

        # handles empty messages
        if not user_query:
            client.chat_postMessage(
                channel=channel,
                text=BOT_MESSAGES["empty_query"],
                thread_ts=thread_ts,
            )
            return

        # Reformulate query for better RAG retrieval
        reformulated_query = reformulate_query(logger, user_query)

        # check if we have an existing conversation
        session_id = get_conversation_session(conversation_key)

        # Query the knowledge base with reformulated query
        kb_response = query_bedrock(reformulated_query, session_id)

        response_text = kb_response["output"]["text"]

        # store a new session if we just started a conversation
        if not session_id and "sessionId" in kb_response:
            store_conversation_session(
                conversation_key,
                kb_response["sessionId"],
                user_id,
                channel,
                thread_ts if context_type == "thread" else None,
            )
        client.chat_postMessage(channel=channel, text=response_text, thread_ts=thread_ts)

    except Exception:
        logger.error("Error processing message", extra={"event_id": event_id, "error": traceback.format_exc()})

        # incase Slack API call fails, we still want to log the error
        try:
            client.chat_postMessage(
                channel=channel,
                text=BOT_MESSAGES["error_response"],
                thread_ts=thread_ts,
            )
        except Exception:
            logger.error("Failed to post error message", extra={"error": traceback.format_exc()})


def get_conversation_session(conversation_key):
    """
    Get existing Bedrock session for this conversation
    """
    try:
        slack_bot_state_table = get_slack_bot_state_table()
        response = slack_bot_state_table.get_item(Key={"pk": conversation_key, "sk": "session"})
        if "Item" in response:
            logger.info("Found existing session", extra={"conversation_key": conversation_key})
            return response["Item"]["session_id"]
        return None
    except Exception:
        logger.error("Error getting session", extra={"error": traceback.format_exc()})
        return None


def store_conversation_session(conversation_key, session_id, user_id, channel_id, thread_ts=None):
    """
    Store new Bedrock session for conversation memory
    """
    try:
        ttl = int(time.time()) + 2592000  # 30 days
        slack_bot_state_table = get_slack_bot_state_table()
        slack_bot_state_table.put_item(
            Item={
                "pk": conversation_key,
                "sk": "session",
                "session_id": session_id,
                "user_id": user_id,
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "created_at": int(time.time()),
                "ttl": ttl,
            }
        )
        logger.info("Stored session", extra={"session_id": session_id, "conversation_key": conversation_key})
    except Exception:
        logger.error("Error storing session", extra={"error": traceback.format_exc()})


def query_bedrock(user_query, session_id=None):
    """
    Query Amazon Bedrock Knowledge Base using RAG (Retrieval-Augmented Generation)

    This function retrieves relevant documents from the knowledge base and generates
    a response using the configured LLM model with guardrails for safety.
    """

    KNOWLEDGEBASE_ID, RAG_MODEL_ID, AWS_REGION, GUARD_RAIL_ID, GUARD_VERSION = get_guardrail_config()
    client = boto3.client(
        service_name="bedrock-agent-runtime",
        region_name=AWS_REGION,
    )
    request_params = {
        "input": {"text": user_query},
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": KNOWLEDGEBASE_ID,
                "modelArn": RAG_MODEL_ID,
                "generationConfiguration": {
                    "guardrailConfiguration": {
                        "guardrailId": GUARD_RAIL_ID,
                        "guardrailVersion": GUARD_VERSION,
                    }
                },
            },
        },
    }

    # add session if we have one for conversation continuity
    if session_id:
        request_params["sessionId"] = session_id
        logger.info("Using existing session", extra={"session_id": session_id})
    else:
        logger.info("Starting new conversation")

    response = client.retrieve_and_generate(**request_params)
    logger.info(
        "Got Bedrock response",
        extra={"session_id": response.get("sessionId"), "has_citations": len(response.get("citations", [])) > 0},
    )
    return response
