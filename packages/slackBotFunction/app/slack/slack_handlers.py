"""
Slack event handlers for @mentions, DMs, and feedback capture.

Design goals:
- Acknowledge Slack events quickly.
- Keep setup_handlers minimal; put real logic in small, testable functions.
- Support mention-only start in channels, follow-ups in bot-owned threads, and 'feedback:' notes.
"""

import re
import time
import json
import os
import boto3
from botocore.exceptions import ClientError

from app.core.config import (
    table,
    bot_token,
    logger,
    BOT_MESSAGES,
    FEEDBACK_PREFIX,
    CHANNEL_TYPE_IM,
    SESSION_SK,
    DEDUP_SK,
    EVENT_PREFIX,
    DM_PREFIX,
    THREAD_PREFIX,
    TTL_EVENT_DEDUP,
)
from app.slack.slack_events import store_feedback


# ================================================================
# Common handler helpers
# ================================================================


def _gate_common(event, body):
    """
    Apply common early checks that are shared across handlers.

    Returns:
        str | None: event_id if processing should continue; None to skip.

    Gates:
    - Missing or duplicate event_id (Slack retry dedupe)
    - Bot/self messages or non-standard subtypes (edits, deletes, etc.)
    """
    event_id = body.get("event_id")
    if not event_id:
        logger.info("Skipping event without event_id")
        return None

    if event.get("bot_id") or event.get("subtype"):
        return None

    if _is_duplicate_event(event_id):
        logger.info(f"Skipping duplicate event: {event_id}")
        return None

    return event_id


def _strip_mentions(text: str) -> str:
    """Remove Slack user mentions like <@U123> or <@U123|alias> from text."""
    return re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", text or "").strip()


def _conversation_key_and_root(event):
    """
    Build a stable conversation scope and its root timestamp.

    DM:
        key = dm#<channel_id>
        root = event.thread_ts or event.ts
    Channel thread:
        key = thread#<channel_id>#<root_ts>
        root = event.thread_ts (or event.ts if thread root is the user’s top-level message)
    """
    channel_id = event["channel"]
    root = event.get("thread_ts") or event.get("ts")
    if event.get("channel_type") == CHANNEL_TYPE_IM:
        return f"{DM_PREFIX}{channel_id}", root
    return f"{THREAD_PREFIX}{channel_id}#{root}", root


# ================================================================
# Event and message handlers
# ================================================================


def app_mention_handler(event, ack, body, client):
    """
    Channel interactions that mention the bot.
    - If text after the mention starts with 'feedback:', store it as additional feedback.
    - Otherwise, forward to the async processing pipeline (Q&A).
    """
    ack()
    event_id = _gate_common(event, body)
    if not event_id:
        return

    channel_id = event["channel"]
    user_id = event.get("user", "unknown")
    conversation_key, thread_root = _conversation_key_and_root(event)

    cleaned = _strip_mentions(event.get("text") or "")
    if cleaned.lower().startswith(FEEDBACK_PREFIX):
        feedback_text = cleaned.split(":", 1)[1].strip() if ":" in cleaned else ""
        try:
            store_feedback(
                conversation_key,
                "additional",
                user_id,
                channel_id,
                thread_root,
                None,
                feedback_text,
            )
        except Exception as e:
            logger.error(f"Failed to store channel feedback via mention: {e}")

        try:
            client.chat_postMessage(
                channel=channel_id,
                text=BOT_MESSAGES["feedback_thanks"],
                thread_ts=thread_root,
            )
        except Exception as e:
            logger.error(f"Failed to post channel feedback ack: {e}")
        return

    # Normal mention -> async processing
    logger.info(f"Processing @mention from user {user_id}", extra={"event_id": event_id})
    _trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})


def dm_message_handler(event, event_id, client):
    """
    Direct messages:
    - 'feedback:' prefix -> store as conversation-scoped additional feedback (no model call).
    - otherwise -> forward to async processing (Q&A).
    """
    if event.get("channel_type") != CHANNEL_TYPE_IM:
        return  # not a DM; the channel handler will evaluate it

    text = (event.get("text") or "").strip()
    channel_id = event["channel"]
    conversation_key, thread_root = _conversation_key_and_root(event)
    user_id = event.get("user", "unknown")

    if text.lower().startswith(FEEDBACK_PREFIX):
        feedback_text = text.split(":", 1)[1].strip() if ":" in text else ""
        try:
            store_feedback(
                conversation_key,
                "additional",
                user_id,
                channel_id,
                thread_root,
                None,
                feedback_text,
            )
        except Exception as e:
            logger.error(f"Failed to store DM additional feedback: {e}")

        try:
            client.chat_postMessage(
                channel=channel_id,
                text=BOT_MESSAGES["feedback_thanks"],
                thread_ts=thread_root,
            )
        except Exception as e:
            logger.error(f"Failed to post DM feedback ack: {e}")
        return

    # Normal DM -> async processing
    _trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})


def channel_message_handler(event, event_id, client):
    """
    Channel messages:
    - Ignore top-level messages (policy: require @mention to start).
    - For replies inside a thread the bot owns (session exists):
        * 'feedback:' prefix -> store additional feedback.
        * otherwise -> treat as follow-up question (no re-mention needed) and forward to async.
    """
    if event.get("channel_type") == CHANNEL_TYPE_IM:
        return  # handled in the DM handler

    text = (event.get("text") or "").strip()
    channel_id = event["channel"]
    thread_root = event.get("thread_ts")
    if not thread_root:
        return  # top-level message; require @mention to start

    conversation_key = f"{THREAD_PREFIX}{channel_id}#{thread_root}"
    try:
        resp = table.get_item(Key={"pk": conversation_key, "sk": SESSION_SK})
        if "Item" not in resp:
            logger.info(f"No session found for thread: {conversation_key}")
            return  # not a bot-owned thread; ignore
        logger.info(f"Found session for thread: {conversation_key}")
    except Exception as e:
        logger.error(f"Error checking thread session: {e}")
        return

    if text.lower().startswith(FEEDBACK_PREFIX):
        feedback_text = text.split(":", 1)[1].strip() if ":" in text else ""
        user_id = event.get("user", "unknown")
        try:
            store_feedback(
                conversation_key,
                "additional",
                user_id,
                channel_id,
                thread_root,
                None,
                feedback_text,
            )
        except Exception as e:
            logger.error(f"Failed to store channel additional feedback: {e}")

        try:
            client.chat_postMessage(
                channel=channel_id,
                text=BOT_MESSAGES["feedback_thanks"],
                thread_ts=thread_root,
            )
        except Exception as e:
            logger.error(f"Failed to post channel feedback ack: {e}")
        return

    # Follow-up in a bot-owned thread (no re-mention required)
    _trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})


def unified_message_handler(event, ack, body, client):
    """Handle all message events - DMs and channel messages"""
    ack()
    event_id = _gate_common(event, body)
    if not event_id:
        return

    # Route to appropriate handler based on message type
    if event.get("channel_type") == CHANNEL_TYPE_IM:
        # DM handling
        dm_message_handler(event, event_id, client)
    else:
        # Channel message handling
        channel_message_handler(event, event_id, client)


def feedback_handler(ack, body, client):
    """Handle feedback button clicks (both positive and negative)."""
    ack()
    try:
        action_id = body["actions"][0]["action_id"]
        feedback_data = json.loads(body["actions"][0]["value"])

        # Check if this is the latest message in the conversation
        conversation_key = feedback_data["ck"]
        message_ts = feedback_data.get("mt")

        if message_ts and not _is_latest_message(conversation_key, message_ts):
            logger.info(f"Feedback ignored - not latest message: {message_ts}")
            return

        # Determine feedback type and response message based on action_id
        if action_id == "feedback_yes":
            feedback_type = "positive"
            response_message = BOT_MESSAGES["feedback_positive_thanks"]
        elif action_id == "feedback_no":
            feedback_type = "negative"
            response_message = BOT_MESSAGES["feedback_negative_thanks"]
        else:
            logger.error(f"Unknown feedback action: {action_id}")
            return

        try:
            store_feedback(
                feedback_data["ck"],
                feedback_type,
                body["user"]["id"],
                feedback_data["ch"],
                feedback_data.get("tt"),
                feedback_data.get("mt"),
            )
            # Only post message if storage succeeded
            client.chat_postMessage(
                channel=feedback_data["ch"],
                text=response_message,
                thread_ts=feedback_data.get("tt"),
            )
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                # Silently ignore duplicate votes - user already voted on this message
                logger.info(f"Duplicate vote ignored for user {body['user']['id']}")
                return
            logger.error(f"Feedback storage error: {e}")
        except Exception as e:
            logger.error(f"Unexpected feedback error: {e}")
    except Exception as e:
        logger.error(f"Error handling feedback: {e}")


# ================================================================
# Registration
# ================================================================


def setup_handlers(app):
    """Register handlers. Intentionally minimal—no branching here."""
    app.event("app_mention")(app_mention_handler)
    app.event("message")(unified_message_handler)
    app.action("feedback_yes")(feedback_handler)
    app.action("feedback_no")(feedback_handler)


# ================================================================
# AWS/Slack infrastructure helpers
# ================================================================


def _is_duplicate_event(event_id):
    """
    Check if we've already processed this event using DynamoDB conditional writes.

    Key:
        pk = f"event#{event_id}", sk = "dedup", ttl = now + 1h
    Behavior:
        - First write succeeds (not a duplicate).
        - Subsequent writes within TTL fail the condition and are treated as duplicates.
    """
    try:
        ttl = int(time.time()) + TTL_EVENT_DEDUP
        table.put_item(
            Item={"pk": f"{EVENT_PREFIX}{event_id}", "sk": DEDUP_SK, "ttl": ttl, "timestamp": int(time.time())},
            ConditionExpression="attribute_not_exists(pk)",
        )
        return False  # Not a duplicate
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return True  # Duplicate
        logger.error("Error checking event duplication", extra={"error": str(e)})
        return False


def _is_latest_message(conversation_key, message_ts):
    """Check if message_ts is the latest bot message using session data"""
    try:
        response = table.get_item(Key={"pk": conversation_key, "sk": SESSION_SK})
        if "Item" in response:
            latest_message_ts = response["Item"].get("latest_message_ts")
            return latest_message_ts == message_ts
        return False
    except Exception as e:
        logger.error(f"Error checking latest message: {e}")
        return False


def _trigger_async_processing(event_data):
    """
    Trigger asynchronous Lambda invocation to process Slack events.

    Slack requires responses within 3 seconds, but Bedrock queries can take longer.
    This function invokes the same Lambda function asynchronously to handle the
    actual AI processing without blocking the initial Slack response.
    """
    try:
        lambda_client = boto3.client("lambda")
        lambda_client.invoke(
            FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"],
            InvocationType="Event",
            Payload=json.dumps({"async_processing": True, "slack_event": event_data}),
        )
        logger.info("Async processing triggered successfully")
    except Exception as e:
        logger.error("Failed to trigger async processing", extra={"error": str(e)})
