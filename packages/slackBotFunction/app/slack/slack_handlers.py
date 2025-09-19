"""
Slack event handlers for @mentions, DMs, and feedback capture.

Design goals:
- Acknowledge Slack events quickly.
- Keep setup_handlers minimal; put real logic in small, testable functions.
- Support mention-only start in channels, follow-ups in bot-owned threads, and 'feedback:' notes.
"""

import json
from functools import lru_cache
import traceback
from typing import Any, Dict
from botocore.exceptions import ClientError
from slack_bolt import Ack, App
from slack_sdk import WebClient
from app.core.config import (
    BOT_MESSAGES,
    get_bot_token,
    get_logger,
    constants,
)
from app.services.dynamo import get_state_information
from app.utils.handler_utils import (
    conversation_key_and_root,
    gate_common,
    is_latest_message,
    strip_mentions,
    trigger_async_processing,
    respond_with_eyes,
    trigger_pull_request_processing,
)
from app.slack.slack_events import store_feedback

logger = get_logger()

# ================================================================
# Registration
# ================================================================


@lru_cache
def setup_handlers(app: App):
    """Register handlers. Intentionally minimal—no branching here."""
    app.event("app_mention")(mention_handler)
    app.event("message")(unified_message_handler)
    app.action("feedback_yes")(feedback_handler)
    app.action("feedback_no")(feedback_handler)


# ================================================================
# Event and message handlers
# ================================================================


def mention_handler(event: Dict[str, Any], ack: Ack, body: Dict[str, Any], client: WebClient):
    """
    Channel interactions that mention the bot.
    - If text after the mention starts with 'feedback:', store it as additional feedback.
    - Otherwise, forward to the async processing pipeline (Q&A).
    """
    bot_token = get_bot_token()
    logger.debug("Sending ack response in mention_handler")
    ack()
    respond_with_eyes(bot_token, event)
    event_id = gate_common(event, body)
    if not event_id:
        return
    original_message_text = (event.get("text") or "").strip()
    user_id = event.get("user", "unknown")
    conversation_key, thread_root = conversation_key_and_root(event)

    message_text = strip_mentions(original_message_text)
    logger.info(f"Processing @mention from user {user_id}", extra={"event_id": event_id})
    _common_message_handler(
        message_text=message_text,
        conversation_key=conversation_key,
        thread_root=thread_root,
        client=client,
        event=event,
        event_id=event_id,
        post_to_thread=True,
        body=body,
    )


def dm_message_handler(event: Dict[str, Any], event_id, client: WebClient, body: Dict[str, Any]):
    """
    Direct messages:
    - 'feedback:' prefix -> store as conversation-scoped additional feedback (no model call).
    - otherwise -> forward to async processing (Q&A).
    """
    if event.get("channel_type") != constants.CHANNEL_TYPE_IM:
        return  # not a DM; the channel handler will evaluate it
    message_text = (event.get("text") or "").strip()
    user_id = event.get("user", "unknown")
    conversation_key, thread_root = conversation_key_and_root(event)
    logger.info(f"Processing DM from user {user_id}", extra={"event_id": event_id})
    _common_message_handler(
        message_text=message_text,
        conversation_key=conversation_key,
        thread_root=thread_root,
        client=client,
        event=event,
        event_id=event_id,
        post_to_thread=False,
        body=body,
    )


def thread_message_handler(event: Dict[str, Any], event_id, client: WebClient, body: Dict[str, Any]):
    """
    Thread messages:
    - Ignore top-level messages (policy: require @mention to start).
    - For replies inside a thread the bot owns (session exists):
        * 'feedback:' prefix -> store additional feedback.
        * otherwise -> treat as follow-up question (no re-mention needed) and forward to async.
    """
    if event.get("channel_type") == constants.CHANNEL_TYPE_IM:
        return  # handled in the DM handler

    message_text = (event.get("text") or "").strip()
    channel_id = event["channel"]
    thread_root = event.get("thread_ts")
    user_id = event.get("user", "unknown")
    if not thread_root:
        return  # top-level message; require @mention to start

    conversation_key = f"{constants.THREAD_PREFIX}{channel_id}#{thread_root}"
    try:
        resp = get_state_information({"pk": conversation_key, "sk": constants.SESSION_SK})
        if "Item" not in resp:
            logger.info(f"No session found for thread: {conversation_key}")
            return  # not a bot-owned thread; ignore
        logger.info(f"Found session for thread: {conversation_key}")
    except Exception as e:
        logger.error(f"Error checking thread session: {e}", extra={"error": traceback.format_exc()})
        return

    logger.info(f"Processing thread message from user {user_id}", extra={"event_id": event_id})
    _common_message_handler(
        message_text=message_text,
        conversation_key=conversation_key,
        thread_root=thread_root,
        client=client,
        event=event,
        event_id=event_id,
        post_to_thread=True,
        body=body,
    )


def unified_message_handler(event: Dict[str, Any], ack: Ack, body: Dict[str, Any], client: WebClient):
    """Handle all message events - DMs and channel messages"""
    logger.debug("Sending ack response")
    ack()
    bot_token = get_bot_token()
    respond_with_eyes(bot_token, event)
    event_id = gate_common(event, body)
    if not event_id:
        return

    # Route to appropriate handler based on message type
    if event.get("channel_type") == constants.CHANNEL_TYPE_IM:
        # DM handling
        dm_message_handler(event=event, event_id=event_id, client=client, body=body)
    else:
        # Channel message handling
        thread_message_handler(event=event, event_id=event_id, client=client, body=body)


def feedback_handler(ack: Ack, body: Dict[str, Any], client: WebClient):
    """Handle feedback button clicks (both positive and negative)."""
    logger.debug("Sending ack response")
    ack()
    try:
        action_id = body["actions"][0]["action_id"]
        feedback_data = json.loads(body["actions"][0]["value"])

        # Check if this is the latest message in the conversation
        conversation_key = feedback_data["ck"]
        message_ts = feedback_data.get("mt")

        if message_ts and not is_latest_message(conversation_key, message_ts):
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
                conversation_key=feedback_data["ck"],
                feedback_type=feedback_type,
                user_id=body["user"]["id"],
                channel_id=feedback_data["ch"],
                thread_ts=feedback_data.get("tt"),
                message_ts=feedback_data.get("mt"),
                client=client,
            )
            # Only post message if storage succeeded
            post_params = {"channel": feedback_data["ch"], "text": response_message}
            if feedback_data.get("tt"):  # Only add thread_ts if it exists (not for DMs)
                post_params["thread_ts"] = feedback_data["tt"]
            client.chat_postMessage(**post_params)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                # Silently ignore duplicate votes - user already voted on this message
                logger.info(f"Duplicate vote ignored for user {body['user']['id']}")
                return
            logger.error(f"Feedback storage error: {e}", extra={"error": traceback.format_exc()})
        except Exception as e:
            logger.error(f"Unexpected feedback error: {e}", extra={"error": traceback.format_exc()})
    except Exception as e:
        logger.error(f"Error handling feedback: {e}", extra={"error": traceback.format_exc()})


# ================================================================
# Common processing for message handlers
# ================================================================


def _common_message_handler(
    message_text: str,
    conversation_key: str,
    thread_root: str,
    client: WebClient,
    event: Dict[str, Any],
    event_id,
    post_to_thread: bool,
    body: Dict[str, Any],
):
    channel_id = event["channel"]
    user_id = event.get("user", "unknown")
    if message_text.lower().startswith(constants.FEEDBACK_PREFIX):
        feedback_text = message_text.split(":", 1)[1].strip() if ":" in message_text else ""
        try:
            store_feedback(
                conversation_key=conversation_key,
                feedback_type="additional",
                user_id=user_id,
                channel_id=channel_id,
                thread_ts=thread_root,
                message_ts=None,
                feedback_text=feedback_text,
                client=client,
            )
        except Exception as e:
            logger.error(f"Failed to store channel feedback via mention: {e}", extra={"error": traceback.format_exc()})
        try:
            params = {
                "channel": channel_id,
                "text": BOT_MESSAGES["feedback_thanks"],
            }

            if post_to_thread:
                params["thread_ts"] = thread_root

            client.chat_postMessage(**params)
        except Exception as e:
            logger.error(f"Failed to post channel feedback ack: {e}", extra={"error": traceback.format_exc()})
        return

    if message_text.lower().startswith(constants.PULL_REQUEST_PREFIX):
        try:
            pull_request_id, extracted_message = _extract_pull_request_id(message_text)
            trigger_pull_request_processing(pull_request_id=pull_request_id, event=event, event_id=event_id)
        except Exception as e:
            logger.error(f"Can not find pull request details: {e}", extra={"error": traceback.format_exc()})
        return

    trigger_async_processing(event=event, event_id=event_id)
