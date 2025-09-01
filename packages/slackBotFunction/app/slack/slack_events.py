"""
Slack event processing
Handles conversation memory, Bedrock queries, and responding back to Slack
"""

import re
import time
import json
import boto3
from slack_sdk import WebClient
from app.core.config import (
    table,
    logger,
    KNOWLEDGEBASE_ID,
    RAG_MODEL_ID,
    AWS_REGION,
    GUARD_RAIL_ID,
    GUARD_VERSION,
    BOT_MESSAGES,
    CONTEXT_TYPE_DM,
    CONTEXT_TYPE_THREAD,
    CHANNEL_TYPE_IM,
    SESSION_SK,
    FEEDBACK_PREFIX_KEY,
    USER_PREFIX,
    DM_PREFIX,
    THREAD_PREFIX,
    NOTE_SUFFIX,
)


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
        raw_text = event["text"]
        user_id = event["user"]
        channel = event["channel"]
        # figure out if this is a DM or channel thread
        if event.get("channel_type") == CHANNEL_TYPE_IM:
            conversation_key = f"{DM_PREFIX}{channel}"
            context_type = CONTEXT_TYPE_DM
            thread_ts = event.get("thread_ts", event["ts"])
        else:
            thread_root = event.get("thread_ts", event["ts"])
            conversation_key = f"{THREAD_PREFIX}{channel}#{thread_root}"
            context_type = CONTEXT_TYPE_THREAD
            thread_ts = thread_root

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

        # check if we have an existing conversation
        session_id = get_conversation_session(conversation_key)

        kb_response = query_bedrock(user_query, session_id)
        response_text = kb_response["output"]["text"]

        # store a new session if we just started a conversation
        if not session_id and "sessionId" in kb_response:
            store_conversation_session(
                conversation_key,
                kb_response["sessionId"],
                user_id,
                channel,
                thread_ts if context_type == CONTEXT_TYPE_THREAD else None,
            )

        # Post the answer (plain) to get message_ts
        post = client.chat_postMessage(
            channel=channel,
            text=response_text,
            thread_ts=thread_ts,
        )
        message_ts = post["ts"]

        # Attach feedback buttons via chat_update (value kept small; no user_query)
        feedback_value = json.dumps({"ck": conversation_key, "ch": channel, "tt": thread_ts, "mt": message_ts})
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": response_text}},
            {
                "type": "section",
                "text": {"type": "plain_text", "text": BOT_MESSAGES["feedback_prompt"]},
            },
            {
                "type": "actions",
                "block_id": "feedback_block",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": BOT_MESSAGES["feedback_yes"]},
                        "action_id": "feedback_yes",
                        "value": feedback_value,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": BOT_MESSAGES["feedback_no"]},
                        "action_id": "feedback_no",
                        "value": feedback_value,
                    },
                ],
            },
        ]
        try:
            client.chat_update(
                channel=channel,
                ts=message_ts,
                text=response_text,
                blocks=blocks,
            )
        except Exception as e:
            logger.error(
                f"Failed to attach feedback buttons: {e}",
                extra={"event_id": event_id, "message_ts": message_ts},
            )

    except Exception as err:
        logger.error(f"Error processing message: {err}", extra={"event_id": event_id})

        # incase Slack API call fails, we still want to log the error
        try:
            client.chat_postMessage(
                channel=channel,
                text=BOT_MESSAGES["error_response"],
                thread_ts=thread_ts,
            )
        except Exception as post_err:
            logger.error(f"Failed to post error message: {post_err}")


def store_feedback(
    conversation_key,
    user_query,
    feedback_type,
    user_id,
    channel_id,
    thread_ts=None,
    message_ts=None,
    additional_feedback=None,
):
    """
    Store user feedback for analytics with rich context.

    Key design:
      - Per-answer vote:   pk="feedback#<conversation_key>#<message_ts>", sk="user#<user_id>"
      - Conversation note: pk="feedback#<conversation_key>",            sk="user#<user_id>#note#<created_at>"

    Idempotency:
      - For votes (positive/negative) with message_ts, we conditionally write to prevent double-votes.
    """
    try:
        now = int(time.time())
        ttl = now + 7776000  # 90 days TTL for automatic cleanup

        # Build keys: per-message votes if message_ts present; else conversation-scoped note
        if message_ts:
            pk = f"{FEEDBACK_PREFIX_KEY}{conversation_key}#{message_ts}"
            sk = f"{USER_PREFIX}{user_id}"
            condition = "attribute_not_exists(pk) AND attribute_not_exists(sk)"
        else:
            pk = f"{FEEDBACK_PREFIX_KEY}{conversation_key}"
            sk = f"{USER_PREFIX}{user_id}{NOTE_SUFFIX}{now}"
            condition = None

        feedback_item = {
            "pk": pk,
            "sk": sk,
            "conversation_key": conversation_key,
            "feedback_type": feedback_type,  # 'positive' | 'negative' | 'additional'
            "user_id": user_id,
            "channel_id": channel_id,
            "created_at": now,
            "ttl": ttl,
        }

        # Optional context
        if thread_ts:
            feedback_item["thread_ts"] = thread_ts
        if message_ts:
            feedback_item["message_ts"] = message_ts
        if user_query:
            feedback_item["user_query"] = user_query[:1000]  # small excerpt to keep items compact
        if additional_feedback:
            feedback_item["additional_feedback"] = additional_feedback[:4000]

        if condition:
            table.put_item(Item=feedback_item, ConditionExpression=condition)
        else:
            table.put_item(Item=feedback_item)

        logger.info(
            "Stored feedback",
            extra={
                "pk": pk,
                "sk": sk,
                "feedback_type": feedback_type,
                "conversation_key": conversation_key,
                "user_id": user_id,
                "has_thread": bool(thread_ts),
                "has_message_ts": bool(message_ts),
                "has_additional": bool(additional_feedback),
            },
        )

    except Exception as e:
        logger.error(
            f"Error storing feedback: {e}",
            extra={"conversation_key": conversation_key, "feedback_type": feedback_type, "user_id": user_id},
        )


def get_conversation_session(conversation_key):
    """
    Get existing Bedrock session for this conversation
    """
    try:
        response = table.get_item(Key={"pk": conversation_key, "sk": SESSION_SK})
        if "Item" in response:
            logger.info(f"Found existing session for {conversation_key}")
            return response["Item"]["session_id"]
        return None
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        return None


def store_conversation_session(conversation_key, session_id, user_id, channel_id, thread_ts=None):
    """
    Store new Bedrock session for conversation memory
    """
    try:
        ttl = int(time.time()) + 2592000  # 30 days
        table.put_item(
            Item={
                "pk": conversation_key,
                "sk": SESSION_SK,
                "session_id": session_id,
                "user_id": user_id,
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "created_at": int(time.time()),
                "ttl": ttl,
            }
        )
        logger.info(f"Stored session {session_id} for {conversation_key}")
    except Exception as e:
        logger.error(f"Error storing session: {e}")


def query_bedrock(user_query, session_id=None):
    """
    Query Amazon Bedrock Knowledge Base using RAG (Retrieval-Augmented Generation)

    This function retrieves relevant documents from the knowledge base and generates
    a response using the configured LLM model with guardrails for safety.
    """

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
        logger.info(f"Using existing session ID: {session_id}")
    else:
        logger.info("Starting new conversation")

    response = client.retrieve_and_generate(**request_params)
    logger.info(
        "Got Bedrock response",
        extra={"session_id": response.get("sessionId"), "has_citations": len(response.get("citations", [])) > 0},
    )
    return response
