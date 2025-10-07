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
)
from app.services.slack import post_error_message
from app.utils.handler_utils import (
    conversation_key_and_root,
    extract_conversation_context,
    extract_session_pull_request_id,
    forward_event_to_pull_request_lambda,
    gate_common,
    is_latest_message,
    respond_with_eyes,
)
from app.slack.slack_events import process_async_slack_event, store_feedback

logger = get_logger()

# ================================================================
# Registration
# ================================================================


@lru_cache
def setup_handlers(app: App) -> None:
    """Register handlers. Intentionally minimal—no branching here."""
    app.event("app_mention")(ack=respond_to_events, lazy=[unified_message_handler])
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


def unified_message_handler(client: WebClient, event: Dict[str, Any], req: BoltRequest, body: Dict[str, Any]) -> None:
    """
    All messages get processed by this code
    If message starts with FEEDBACK_PREFIX then handle feedback message and return
    If message starts with PULL_REQUEST_PREFIX then trigger lambda in pull request and return
    Otherwise, call process_async_slack_event to process the event

    """
    event_id = gate_common(event=event, body=body)
    if not event_id:
        return
    user_id = event.get("user", "unknown")
    conversation_key, _ = conversation_key_and_root(event=event)
    conversation_key, _, _ = extract_conversation_context(event)
    session_pull_request_id = extract_session_pull_request_id(conversation_key)
    if session_pull_request_id:
        logger.info(
            f"Message in pull request session {session_pull_request_id} from user {user_id}",
            extra={"session_pull_request_id": session_pull_request_id},
        )
        forward_event_to_pull_request_lambda(req=req, pull_request_id=session_pull_request_id, forward_type="event")
        return

    # note - we dont do post an error message if this fails as its handled by process_async_slack_event
    try:
        process_async_slack_event(event=event, event_id=event_id, client=client)
    except Exception:
        logger.error("Error triggering async processing", extra={"error": traceback.format_exc()})
