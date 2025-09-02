"""
Slack event processing
Handles conversation memory, Bedrock queries, and responding back to Slack
"""

import re
import time
import json
import boto3
from botocore.exceptions import ClientError
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
    TTL_FEEDBACK,
    TTL_SESSION,
)
from app.services.query_reformulator import reformulate_query


def cleanup_previous_unfeedback_qa(conversation_key, current_message_ts, session_data):
    """Delete previous Q&A pair if no feedback received"""
    try:
        previous_message_ts = session_data.get("latest_message_ts")
        if not previous_message_ts or previous_message_ts == current_message_ts:
            return

        # Check if previous Q&A has any feedback
        feedback_exists = check_feedback_exists(conversation_key, previous_message_ts)

        if not feedback_exists:
            # Delete unfeedback Q&A pair for privacy
            previous_qa_key = f"qa#{conversation_key}#{previous_message_ts}"
            table.delete_item(Key={"pk": previous_qa_key, "sk": "turn"})
            logger.info("Deleted unfeedback Q&A for privacy", extra={"message_ts": previous_message_ts})

    except Exception as e:
        logger.error("Error cleaning up unfeedback Q&A", extra={"error": str(e)})


def check_feedback_exists(conversation_key, message_ts):
    """Check if any feedback exists for this Q&A pair"""
    try:
        response = table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": f"feedback#{conversation_key}#{message_ts}"},
            Limit=1,
        )
        return len(response.get("Items", [])) > 0
    except Exception:
        return False


def store_qa_pair(conversation_key, user_query, bot_response, message_ts, session_id, user_id):
    """
    Store Q&A pair for feedback correlation
    """
    try:
        table.put_item(
            Item={
                "pk": f"qa#{conversation_key}#{message_ts}",
                "sk": "turn",
                "user_query": user_query[:1000] if user_query else None,
                "bot_response": bot_response[:2000] if bot_response else None,
                "session_id": session_id,
                "user_id": user_id,
                "message_ts": message_ts,
                "created_at": int(time.time()),
                "ttl": int(time.time()) + TTL_FEEDBACK,
            }
        )
        logger.info("Stored Q&A pair", extra={"conversation_key": conversation_key, "message_ts": message_ts})
    except Exception as e:
        logger.error("Failed to store Q&A pair", extra={"error": str(e)})


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

        # Reformulate query for better RAG retrieval
        reformulated_query = reformulate_query(logger, user_query)

        # check if we have an existing conversation
        session_data = get_conversation_session_data(conversation_key)
        session_id = session_data.get("session_id") if session_data else None

        # Query the knowledge base with reformulated query
        kb_response = query_bedrock(reformulated_query, session_id)

        response_text = kb_response["output"]["text"]

        # Post the answer (plain) to get message_ts
        post = client.chat_postMessage(
            channel=channel,
            text=response_text,
            thread_ts=thread_ts,
        )
        message_ts = post["ts"]

        # store a new session if we just started a conversation
        if not session_id and "sessionId" in kb_response:
            store_conversation_session(
                conversation_key,
                kb_response["sessionId"],
                user_id,
                channel,
                thread_ts if context_type == CONTEXT_TYPE_THREAD else None,
                message_ts,
            )
        elif session_id:
            # Clean up previous unfeedback Q&A before storing new one
            cleanup_previous_unfeedback_qa(conversation_key, message_ts, session_data)
            # Update existing session with latest message timestamp
            update_session_latest_message(conversation_key, message_ts)

        # Store Q&A pair for feedback correlation
        store_qa_pair(
            conversation_key=conversation_key,
            user_query=user_query,
            bot_response=response_text,
            message_ts=message_ts,
            session_id=kb_response.get("sessionId"),
            user_id=user_id,
        )

        # Attach feedback buttons via chat_update
        feedback_value = json.dumps(
            {"ck": conversation_key, "ch": channel, "tt": thread_ts, "mt": message_ts}, separators=(",", ":")
        )
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
        logger.error("Error processing message", extra={"event_id": event_id, "error": str(err)})

        # incase Slack API call fails, we still want to log the error
        try:
            client.chat_postMessage(
                channel=channel,
                text=BOT_MESSAGES["error_response"],
                thread_ts=thread_ts,
            )
        except Exception as post_err:
            logger.error("Failed to post error message", extra={"error": str(post_err)})


def store_feedback_with_qa(
    conversation_key,
    user_query,
    bot_response,
    feedback_type,
    user_id,
    channel_id,
    thread_ts=None,
    message_ts=None,
    additional_feedback=None,
):
    """
    Store user feedback with Q&A context using message_ts linking
    """
    try:
        # Use latest_message_ts for both button and text feedback
        if not message_ts:
            message_ts = get_latest_message_ts(conversation_key)

        # Retrieve Q&A data if not provided and we have message_ts
        if message_ts and (not user_query or not bot_response):
            try:
                qa_response = table.get_item(Key={"pk": f"qa#{conversation_key}#{message_ts}", "sk": "turn"})
                if "Item" in qa_response:
                    qa_item = qa_response["Item"]
                    user_query = user_query or qa_item.get("user_query")
                    bot_response = bot_response or qa_item.get("bot_response")
            except Exception as e:
                logger.error(f"Error retrieving Q&A data: {e}")

        now = int(time.time())
        ttl = now + TTL_FEEDBACK

        if message_ts:
            pk = f"{FEEDBACK_PREFIX_KEY}{conversation_key}#{message_ts}"
            sk = f"{USER_PREFIX}{user_id}"
        else:
            # Fallback if no message_ts available (shouldn't happen in normal flow)
            pk = f"{FEEDBACK_PREFIX_KEY}{conversation_key}"
            sk = f"{USER_PREFIX}{user_id}{NOTE_SUFFIX}{now}"

        feedback_item = {
            "pk": pk,
            "sk": sk,
            "conversation_key": conversation_key,
            "feedback_type": feedback_type,
            "user_id": user_id,
            "channel_id": channel_id,
            "created_at": now,
            "ttl": ttl,
            "user_query": user_query[:1000] if user_query else None,
            "bot_response": bot_response[:2000] if bot_response else None,
        }

        if thread_ts:
            feedback_item["thread_ts"] = thread_ts
        if message_ts:
            feedback_item["message_ts"] = message_ts
        if additional_feedback:
            feedback_item["additional_feedback"] = additional_feedback[:4000]

        table.put_item(Item=feedback_item)
        logger.info("Stored feedback with Q&A context", extra={"pk": pk, "sk": sk})

    except Exception as e:
        logger.error("Error storing feedback", extra={"error": str(e)})


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
        ttl = now + TTL_FEEDBACK

        # Use latest_message_ts consistently for both button and text feedback
        if not message_ts:
            message_ts = get_latest_message_ts(conversation_key)

        if message_ts:
            pk = f"{FEEDBACK_PREFIX_KEY}{conversation_key}#{message_ts}"
            sk = f"{USER_PREFIX}{user_id}"
            condition = "attribute_not_exists(pk) AND attribute_not_exists(sk)"
        else:
            # Fallback if no message_ts available (shouldn't happen in normal flow)
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

    except ClientError as e:
        # Re-raise ClientError so caller can handle ConditionalCheckFailedException
        logger.error(
            f"Error storing feedback: {e}",
            extra={"conversation_key": conversation_key, "feedback_type": feedback_type, "user_id": user_id},
        )
        raise
    except Exception as e:
        logger.error(
            f"Error storing feedback: {e}",
            extra={"conversation_key": conversation_key, "feedback_type": feedback_type, "user_id": user_id},
        )


def get_conversation_session(conversation_key):
    """
    Get existing Bedrock session for this conversation
    """
    session_data = get_conversation_session_data(conversation_key)
    return session_data.get("session_id") if session_data else None


def get_conversation_session_data(conversation_key):
    """
    Get full session data for this conversation
    """
    try:
        response = table.get_item(Key={"pk": conversation_key, "sk": SESSION_SK})
        if "Item" in response:
            logger.info("Found existing session", extra={"conversation_key": conversation_key})
            return response["Item"]
        return None
    except Exception as e:
        logger.error("Error getting session", extra={"error": str(e)})
        return None


def get_latest_message_ts(conversation_key):
    """
    Get latest message timestamp from session
    """
    try:
        response = table.get_item(Key={"pk": conversation_key, "sk": SESSION_SK})
        if "Item" in response:
            return response["Item"].get("latest_message_ts")
        return None
    except Exception as e:
        logger.error("Error getting latest message timestamp", extra={"error": str(e)})
        return None


def store_conversation_session(
    conversation_key, session_id, user_id, channel_id, thread_ts=None, latest_message_ts=None
):
    """
    Store new Bedrock session for conversation memory
    """
    try:
        ttl = int(time.time()) + TTL_SESSION
        item = {
            "pk": conversation_key,
            "sk": SESSION_SK,
            "session_id": session_id,
            "user_id": user_id,
            "channel_id": channel_id,
            "created_at": int(time.time()),
            "ttl": ttl,
        }
        # Add thread context for channel conversations (not needed for DMs)
        if thread_ts:
            item["thread_ts"] = thread_ts
        # Track latest bot message timestamp for feedback restriction
        if latest_message_ts:
            item["latest_message_ts"] = latest_message_ts

        table.put_item(Item=item)
        logger.info("Stored session", extra={"session_id": session_id, "conversation_key": conversation_key})
    except Exception as e:
        logger.error("Error storing session", extra={"error": str(e)})


def update_session_latest_message(conversation_key, message_ts):
    """
    Update session with latest message timestamp
    """
    try:
        table.update_item(
            Key={"pk": conversation_key, "sk": SESSION_SK},
            UpdateExpression="SET latest_message_ts = :ts",
            ExpressionAttributeValues={":ts": message_ts},
        )
    except Exception as e:
        logger.error("Error updating session latest message", extra={"error": str(e)})


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
        logger.info("Using existing session", extra={"session_id": session_id})
    else:
        logger.info("Starting new conversation")

    response = client.retrieve_and_generate(**request_params)
    logger.info(
        "Got Bedrock response",
        extra={"session_id": response.get("sessionId"), "has_citations": len(response.get("citations", [])) > 0},
    )
    return response
