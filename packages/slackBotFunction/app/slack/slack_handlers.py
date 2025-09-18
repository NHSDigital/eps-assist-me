"""
Slack event handlers for @mentions, DMs, and feedback capture.

Design goals:
- Acknowledge Slack events quickly.
- Keep setup_handlers minimal; put real logic in small, testable functions.
- Support mention-only start in channels, follow-ups in bot-owned threads, and 'feedback:' notes.
"""

import json
import re
from functools import lru_cache
import traceback
from botocore.exceptions import ClientError
from app.core.config import (
    get_bot_messages,
    get_bot_token,
    get_logger,
    constants,
)
from app.services.dynamo import get_state_information
from app.utils.handler_utils import (
    is_duplicate_event,
    trigger_async_processing,
    respond_with_eyes,
    trigger_pull_request_processing,
)
from app.slack.slack_events import store_feedback

logger = get_logger()

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

    if is_duplicate_event(event_id):
        logger.info(f"Skipping duplicate event: {event_id}")
        return None

    return event_id


def _strip_mentions(text: str) -> str:
    """Remove Slack user mentions like <@U123> or <@U123|alias> from text."""
    return re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", text or "").strip()


def _extract_pull_request_id(text: str) -> str:
    # Regex: '#pr' + optional space + number + space + rest of text
    pattern = r"#pr\s*(\d+)\s+(.+)"
    match = re.match(pattern, text)
    if not match:
        raise ValueError("Text does not match expected format (#pr <number> <text>)")
    pr_number = int(match.group(1))
    rest_text = match.group(2)
    return pr_number, rest_text


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
    if event.get("channel_type") == constants.CHANNEL_TYPE_IM:
        return f"{constants.DM_PREFIX}{channel_id}", root
    return f"{constants.THREAD_PREFIX}{channel_id}#{root}", root


# ================================================================
# Event and message handlers
# ================================================================


def mention_handler(event, ack, body, client):
    """
    Channel interactions that mention the bot.
    - If text after the mention starts with 'feedback:', store it as additional feedback.
    - Otherwise, forward to the async processing pipeline (Q&A).
    """
    bot_token = get_bot_token()
    logger.debug("Sending ack response")
    ack()
    respond_with_eyes(bot_token, event)
    event_id = _gate_common(event, body)
    if not event_id:
        return
    original_message_text = (event.get("text") or "").strip()
    channel_id = event["channel"]
    user_id = event.get("user", "unknown")
    conversation_key, thread_root = _conversation_key_and_root(event)

    message_text = _strip_mentions(original_message_text)
    _common_message_handler(
        message_text=message_text,
        conversation_key=conversation_key,
        user_id=user_id,
        channel_id=channel_id,
        thread_root=thread_root,
        client=client,
        event=event,
        event_id=event_id,
        bot_token=bot_token,
    )


def dm_message_handler(event, event_id, client):
    """
    Direct messages:
    - 'feedback:' prefix -> store as conversation-scoped additional feedback (no model call).
    - otherwise -> forward to async processing (Q&A).
    """
    if event.get("channel_type") != constants.CHANNEL_TYPE_IM:
        return  # not a DM; the channel handler will evaluate it
    bot_token = get_bot_token()
    message_text = (event.get("text") or "").strip()
    channel_id = event["channel"]
    user_id = event.get("user", "unknown")
    conversation_key, thread_root = _conversation_key_and_root(event)
    _common_message_handler(
        message_text=message_text,
        conversation_key=conversation_key,
        user_id=user_id,
        channel_id=channel_id,
        thread_root=thread_root,
        client=client,
        event=event,
        event_id=event_id,
        bot_token=bot_token,
    )


def thread_message_handler(event, event_id, client):
    """
    Thread messages:
    - Ignore top-level messages (policy: require @mention to start).
    - For replies inside a thread the bot owns (session exists):
        * 'feedback:' prefix -> store additional feedback.
        * otherwise -> treat as follow-up question (no re-mention needed) and forward to async.
    """
    if event.get("channel_type") == constants.CHANNEL_TYPE_IM:
        return  # handled in the DM handler

    text = (event.get("text") or "").strip()
    channel_id = event["channel"]
    thread_root = event.get("thread_ts")
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

    if text.lower().startswith(constants.FEEDBACK_PREFIX):
        feedback_text = text.split(":", 1)[1].strip() if ":" in text else ""
        user_id = event.get("user", "unknown")
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
            logger.error(f"Failed to store channel additional feedback: {e}", extra={"error": traceback.format_exc()})

        try:
            BOT_MESSAGES = get_bot_messages()

            client.chat_postMessage(
                channel=channel_id,
                text=BOT_MESSAGES["feedback_thanks"],
                thread_ts=thread_root,
            )
        except Exception as e:
            logger.error(f"Failed to post channel feedback ack: {e}", extra={"error": traceback.format_exc()})
        return

    # Follow-up in a bot-owned thread (no re-mention required)
    bot_token = get_bot_token()
    trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})


def unified_message_handler(event, ack, body, client):
    """Handle all message events - DMs and channel messages"""
    logger.debug("Sending ack response")
    ack()
    bot_token = get_bot_token()
    respond_with_eyes(bot_token, event)
    event_id = _gate_common(event, body)
    if not event_id:
        return

    # Route to appropriate handler based on message type
    if event.get("channel_type") == constants.CHANNEL_TYPE_IM:
        # DM handling
        dm_message_handler(event, event_id, client)
    else:
        # Channel message handling
        thread_message_handler(event, event_id, client)


def feedback_handler(ack, body, client):
    """Handle feedback button clicks (both positive and negative)."""
    logger.debug("Sending ack response")
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
        BOT_MESSAGES = get_bot_messages()

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
# Registration
# ================================================================


@lru_cache
def setup_handlers(app):
    """Register handlers. Intentionally minimal—no branching here."""
    app.event("app_mention")(mention_handler)
    app.event("message")(unified_message_handler)
    app.action("feedback_yes")(feedback_handler)
    app.action("feedback_no")(feedback_handler)


# ================================================================
# AWS/Slack infrastructure helpers
# ================================================================


def _is_latest_message(conversation_key, message_ts):
    """Check if message_ts is the latest bot message using session data"""
    try:
        response = get_state_information({"pk": conversation_key, "sk": constants.SESSION_SK})
        if "Item" in response:
            latest_message_ts = response["Item"].get("latest_message_ts")
            return latest_message_ts == message_ts
        return False
    except Exception as e:
        logger.error(f"Error checking latest message: {e}", extra={"error": traceback.format_exc()})
        return False


def _common_message_handler(
    message_text: str,
    conversation_key: str,
    user_id: str,
    channel_id: str,
    thread_root: str,
    client,
    event,
    event_id,
    bot_token,
):
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
        BOT_MESSAGES = get_bot_messages()
        try:
            client.chat_postMessage(
                channel=channel_id,
                text=BOT_MESSAGES["feedback_thanks"],
                thread_ts=thread_root,
            )
        except Exception as e:
            logger.error(f"Failed to post channel feedback ack: {e}", extra={"error": traceback.format_exc()})
        return

    if message_text.lower().startswith(constants.PULL_REQUEST_PREFIX):
        try:
            pull_request_id, extracted_message = _extract_pull_request_id(message_text)
            pull_request_lambda_arn = trigger_pull_request_processing(pull_request_id)
            logger.debug(
                f"Handling message for pull request {pull_request_id}",
                extra={"pull_request_id": pull_request_id, "pull_request_lambda_arn": pull_request_lambda_arn},
            )
            client.chat_postMessage(
                channel=channel_id,
                text=f"Handling message for pull request {pull_request_id} by calling {pull_request_lambda_arn}",
                thread_ts=thread_root,
            )
        except Exception as e:
            logger.error(f"Can not find pull request details: {e}", extra={"error": traceback.format_exc()})
        return

    # Normal mention -> async processing
    logger.info(f"Processing @mention from user {user_id}", extra={"event_id": event_id})
    trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})
