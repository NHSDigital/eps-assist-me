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
from slack_bolt import Ack, App, BoltRequest
from slack_sdk import WebClient
from app.core.config import (
    bot_messages,
    get_logger,
    constants,
)
from app.services.dynamo import get_state_information
from app.services.slack import post_error_message
from app.utils.handler_utils import (
    conversation_key_and_root,
    extract_conversation_context,
    extract_pull_request_id,
    extract_session_pull_request_id,
    forward_event_to_pull_request_lambda,
    gate_common,
    is_latest_message,
    strip_mentions,
    respond_with_eyes,
    trigger_pull_request_processing,
)
from app.slack.slack_events import process_async_slack_event, store_feedback

logger = get_logger()

# ================================================================
# Registration
# ================================================================


@lru_cache
def setup_handlers(app: App) -> None:
    """Register handlers. Intentionally minimal—no branching here."""
    app.event("app_mention")(ack=respond_to_events, lazy=[mention_handler])
    app.event("message")(ack=respond_to_events, lazy=[unified_message_handler])
    app.action("feedback_yes")(ack=respond_to_action, lazy=[feedback_handler])
    app.action("feedback_no")(ack=respond_to_action, lazy=[feedback_handler])


# ================================================================
# Event and message handlers
# ================================================================


# ack function for events where we respond with eyes
def respond_to_events(event: Dict[str, Any], ack: Ack, client: WebClient):
    respond_with_eyes(event=event, client=client)
    logger.debug("Sending ack response")
    ack()


# ack function for actions where we just send an ack response back
def respond_to_action(ack: Ack):
    logger.debug("Sending ack response")
    ack()


def mention_handler(event: Dict[str, Any], body: Dict[str, Any], client: WebClient, req: BoltRequest) -> None:
    """
    Channel interactions that mention the bot.
    Pulls some details unique to mentions and removes slack user name
    And then forwards to _common_message_handler
    """
    event_id = gate_common(event=event, body=body)
    if not event_id:
        return
    original_message_text = (event.get("text") or "").strip()
    user_id = event.get("user", "unknown")
    conversation_key, thread_root = conversation_key_and_root(event=event)

    message_text = strip_mentions(message_text=original_message_text)
    logger.info(f"Processing @mention from user {user_id}", extra={"event_id": event_id})
    _common_message_handler(
        message_text=message_text,
        conversation_key=conversation_key,
        thread_root=thread_root,
        client=client,
        event=event,
        event_id=event_id,
        post_to_thread=True,
        req=req,
    )


def dm_message_handler(event: Dict[str, Any], event_id: str, client: WebClient, req: BoltRequest) -> None:
    """
    Direct messages:
    Pulls some details unique to direct messages
    And then forwards to _common_message_handler
    """
    if event.get("channel_type") != constants.CHANNEL_TYPE_IM:
        return  # not a DM; the channel handler will evaluate it
    message_text = (event.get("text") or "").strip()
    user_id = event.get("user", "unknown")
    conversation_key, thread_root = conversation_key_and_root(event=event)
    logger.info(
        f"Processing DM from user {user_id}",
        extra={"event_id": event_id, "conversation_key": conversation_key, "thread_root": thread_root},
    )
    _common_message_handler(
        message_text=message_text,
        conversation_key=conversation_key,
        thread_root=thread_root,
        client=client,
        event=event,
        event_id=event_id,
        post_to_thread=True,
        req=req,
    )


def thread_message_handler(event: Dict[str, Any], event_id: str, client: WebClient, req: BoltRequest) -> None:
    """
    Thread messages:
    Pulls some details unique to threads
    And then forwards to _common_message_handler
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
        resp = get_state_information(key={"pk": conversation_key, "sk": constants.SESSION_SK})
        if "Item" not in resp:
            logger.info(f"No session found for thread: {conversation_key}")
            return  # not a bot-owned thread; ignore
        logger.info(f"Found session for thread: {conversation_key}")
    except Exception as e:
        logger.error(f"Error checking thread session: {e}", extra={"error": traceback.format_exc()})
        _, _, thread_ts = extract_conversation_context(event)
        post_error_message(channel=channel_id, thread_ts=thread_ts, client=client)
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
        req=req,
    )


def unified_message_handler(event: Dict[str, Any], body: Dict[str, Any], client: WebClient, req: BoltRequest) -> None:
    """Handle message events (but not app mentions) - DMs and channel messages"""
    event_id = gate_common(event=event, body=body)
    if not event_id:
        return

    # Route to appropriate handler based on message type
    if event.get("channel_type") == constants.CHANNEL_TYPE_IM:
        # DM handling
        dm_message_handler(event=event, event_id=event_id, client=client, req=req)
    else:
        # Channel message handling
        thread_message_handler(event=event, event_id=event_id, client=client, req=req)


def feedback_handler(body: Dict[str, Any], client: WebClient, req: BoltRequest) -> None:
    """Handle feedback button clicks (both positive and negative)."""
    try:
        channel_id = body["channel"]["id"]
        action_id = body["actions"][0]["action_id"]
        feedback_data = json.loads(body["actions"][0]["value"])

        # Check if this is the latest message in the conversation
        conversation_key = feedback_data["ck"]
        message_ts = feedback_data.get("mt")
        session_pull_request_id = extract_session_pull_request_id(conversation_key)
        if session_pull_request_id:
            logger.info(
                f"Feedback in pull request session {session_pull_request_id}",
                extra={"session_pull_request_id": session_pull_request_id},
            )
            forward_event_to_pull_request_lambda(
                req=req, pull_request_id=session_pull_request_id, forward_type="feedback"
            )
            return

        if message_ts and not is_latest_message(conversation_key=conversation_key, message_ts=message_ts):
            logger.info(f"Feedback ignored - not latest message: {message_ts}")
            return

        # Determine feedback type and response message based on action_id
        if action_id == "feedback_yes":
            feedback_type = "positive"
            response_message = bot_messages.FEEDBACK_POSITIVE_THANKS
        elif action_id == "feedback_no":
            feedback_type = "negative"
            response_message = bot_messages.FEEDBACK_NEGATIVE_THANKS
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
            thread_ts = feedback_data.get("tt")
            post_error_message(channel=channel_id, thread_ts=thread_ts, client=client)
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
    event_id: str,
    post_to_thread: bool,
    req: BoltRequest,
) -> None:
    """
    All messages get processed by this code
    If message starts with FEEDBACK_PREFIX then handle feedback message and return
    If message starts with PULL_REQUEST_PREFIX then trigger lambda in pull request and return
    Otherwise, call process_async_slack_event to process the event

    """
    channel_id = event["channel"]
    user_id = event.get("user", "unknown")
    conversation_key, _, thread_ts = extract_conversation_context(event)
    session_pull_request_id = extract_session_pull_request_id(conversation_key)
    if session_pull_request_id:
        logger.info(
            f"Message in pull request session {session_pull_request_id} from user {user_id}",
            extra={"session_pull_request_id": session_pull_request_id},
        )
        forward_event_to_pull_request_lambda(req=req, pull_request_id=session_pull_request_id, forward_type="event")
        return
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

            params = {
                "channel": channel_id,
                "text": bot_messages.FEEDBACK_THANKS,
            }

            if post_to_thread:
                params["thread_ts"] = thread_root

            client.chat_postMessage(**params)
        except Exception as e:
            logger.error(f"Failed to post channel feedback ack: {e}", extra={"error": traceback.format_exc()})
            _, _, thread_ts = extract_conversation_context(event)
            post_error_message(channel=channel_id, thread_ts=thread_ts, client=client)
        return

    if message_text.lower().startswith(constants.PULL_REQUEST_PREFIX):
        try:
            pull_request_id, _ = extract_pull_request_id(message_text)
            trigger_pull_request_processing(pull_request_id=pull_request_id, event=event, event_id=event_id)
        except Exception as e:
            logger.error(f"Can not find pull request details: {e}", extra={"error": traceback.format_exc()})
            post_error_message(channel=channel_id, thread_ts=thread_ts, client=client)
        return

    # note - we dont do post an error message if this fails as its handled by process_async_slack_event
    try:
        process_async_slack_event(event=event, event_id=event_id, client=client)
    except Exception:
        logger.error("Error triggering async processing", extra={"error": traceback.format_exc()})
