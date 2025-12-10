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
from slack_bolt import Ack, App
from slack_sdk import WebClient
from app.core.config import (
    get_logger,
)
from app.utils.handler_utils import (
    conversation_key_and_root,
    extract_session_pull_request_id,
    forward_action_to_pull_request_lambda,
    forward_event_to_pull_request_lambda,
    gate_common,
    respond_with_eyes,
    should_reply_to_message,
)
from app.slack.slack_events import process_async_slack_action, process_async_slack_event

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
    for i in range(1, 10):
        app.action(f"cite_{i}")(ack=respond_to_action, lazy=[feedback_handler])


# ================================================================
# Event and message handlers
# ================================================================


# ack function for events where we respond with eyes
def respond_to_events(event: Dict[str, Any], ack: Ack, client: WebClient):
    if should_reply_to_message(event, client):
        respond_with_eyes(event=event, client=client)
    logger.debug("Sending ack response")
    ack()


# ack function for actions where we just send an ack response back
def respond_to_action(ack: Ack):
    logger.debug("Sending ack response")
    ack()


def feedback_handler(body: Dict[str, Any], client: WebClient) -> None:
    """Handle feedback button clicks (both positive and negative)."""
    try:
        feedback_data = json.loads(body["actions"][0]["value"])

        # Check if this is the latest message in the conversation
        conversation_key = feedback_data["ck"]
        session_pull_request_id = extract_session_pull_request_id(conversation_key)
        if session_pull_request_id:
            logger.info(
                f"Feedback in pull request session {session_pull_request_id}",
                extra={"session_pull_request_id": session_pull_request_id},
            )
            forward_action_to_pull_request_lambda(body=body, pull_request_id=session_pull_request_id)
            return
        process_async_slack_action(body=body, client=client)
    except Exception as e:
        logger.error(f"Error handling feedback: {e}", extra={"error": traceback.format_exc()})


# ================================================================
# Common processing for message handlers
# ================================================================


def unified_message_handler(client: WebClient, event: Dict[str, Any], body: Dict[str, Any]) -> None:
    """
    All messages get processed by this code
    If message starts with FEEDBACK_PREFIX then handle feedback message and return
    If message starts with PULL_REQUEST_PREFIX then trigger lambda in pull request and return
    Otherwise, call process_async_slack_event to process the event

    """
    event_id = gate_common(event=event, body=body)
    logger.debug("logging result of gate_common", extra={"event_id": event_id, "body": body})
    if not event_id:
        return
    # if its in a group chat
    # and its a message
    # and its not in a thread
    # then ignore it as it will be handled as an app_mention event
    if not should_reply_to_message(event, client):
        logger.debug("Ignoring message in group chat not in a thread or bot not in thread", extra={"event": event})
        # ignore messages in group chats or threads where bot wasn't mentioned
        return
    user_id = event.get("user", "unknown")
    conversation_key, _ = conversation_key_and_root(event=event)
    session_pull_request_id = extract_session_pull_request_id(conversation_key)
    if session_pull_request_id:
        logger.info(
            f"Message in pull request session {session_pull_request_id} from user {user_id}",
            extra={"session_pull_request_id": session_pull_request_id},
        )
        forward_event_to_pull_request_lambda(
            event=event, pull_request_id=session_pull_request_id, event_id=event_id, store_pull_request_id=False
        )
        return

    # note - we dont do post an error message if this fails as its handled by process_async_slack_event
    try:
        process_async_slack_event(event=event, event_id=event_id, client=client)
    except Exception:
        logger.error("Error triggering async processing", extra={"error": traceback.format_exc()})
