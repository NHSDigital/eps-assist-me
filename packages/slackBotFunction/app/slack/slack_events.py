"""
Slack event processing
Handles conversation memory, Bedrock queries, and responding back to Slack
"""

import re
import time
import traceback
import json
from typing import Any, Dict
from botocore.exceptions import ClientError
from slack_sdk import WebClient
from app.core.config import (
    bot_messages,
    constants,
    get_bot_token,
    get_logger,
)

from app.services.dynamo import (
    delete_state_information,
    get_state_information,
    store_state_information,
    update_state_information,
)

from app.services.slack import get_friendly_channel_name, post_error_message
from app.utils.handler_utils import (
    conversation_key_and_root,
    extract_pull_request_id,
    forward_event_to_pull_request_lambda,
    is_duplicate_event,
    is_latest_message,
    strip_mentions,
)

from app.services.ai_processor import process_ai_query


logger = get_logger()


# ================================================================
# Privacy and Q&A management helpers
# ================================================================


def cleanup_previous_unfeedback_qa(
    conversation_key: str, current_message_ts: str, session_data: Dict[str, Any]
) -> None:
    """Delete previous Q&A pair if no feedback received using atomic operation"""
    try:
        previous_message_ts = session_data.get("latest_message_ts")
        # Skip if no previous message or it's the same as current
        if not previous_message_ts or previous_message_ts == current_message_ts:
            return

        # Atomically delete Q&A only if no feedback received
        delete_state_information(
            f"qa#{conversation_key}#{previous_message_ts}", "turn", "attribute_not_exists(feedback_received)"
        )
        logger.info("Deleted unfeedback Q&A for privacy", extra={"message_ts": previous_message_ts})

    except ClientError as e:
        if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            logger.info("Q&A has feedback - keeping for user", extra={"message_ts": previous_message_ts})
        else:
            logger.error("Error cleaning up Q&A", extra={"error": traceback.format_exc()})
    except Exception:
        logger.error("Error cleaning up unfeedback Q&A", extra={"error": traceback.format_exc()})


def store_qa_pair(
    conversation_key: str, user_query: str, bot_response: str, message_ts: str, session_id: str, user_id: str
) -> None:
    """
    Store Q&A pair for feedback correlation
    """
    try:
        item = {
            "pk": f"qa#{conversation_key}#{message_ts}",
            "sk": "turn",
            "user_query": user_query[:1000] if user_query else None,
            "bot_response": bot_response[:2000] if bot_response else None,
            "session_id": session_id,
            "user_id": user_id,
            "message_ts": message_ts,
            "created_at": int(time.time()),
            "ttl": int(time.time()) + constants.TTL_FEEDBACK,
        }
        store_state_information(item=item)
        logger.info("Stored Q&A pair", extra={"conversation_key": conversation_key, "message_ts": message_ts})
    except Exception:
        logger.error("Failed to store Q&A pair", extra={"error": traceback.format_exc()})


def _mark_qa_feedback_received(conversation_key: str, message_ts: str) -> None:
    """
    Mark Q&A record as having received feedback to prevent deletion
    """
    try:
        update_state_information(
            {"pk": f"qa#{conversation_key}#{message_ts}", "sk": "turn"},
            "SET feedback_received = :val",
            {":val": True},
        )
    except Exception:
        logger.error("Error marking Q&A feedback received", extra={"error": traceback.format_exc()})


# ================================================================
# Event processing helpers
# ================================================================


def _handle_session_management(
    conversation_key: str,
    session_data: Dict[str, Any],
    session_id: str,
    kb_response: Dict[str, Any],
    user_id: str,
    channel: str,
    thread_ts: str,
    message_ts: str,
) -> None:
    """Handle Bedrock session creation and cleanup"""
    # Handle conversation session management
    if not session_id and "sessionId" in kb_response:
        # Store new Bedrock session for conversation continuity
        store_conversation_session(
            conversation_key,
            kb_response["sessionId"],
            user_id,
            channel,
            thread_ts,
            message_ts,
        )
    elif session_id:
        # Clean up previous unfeedback Q&A for privacy compliance
        cleanup_previous_unfeedback_qa(conversation_key, message_ts, session_data)
        # Track latest bot message for feedback validation
        update_session_latest_message(conversation_key, message_ts)


def _create_feedback_blocks(
    response_text: str,
    citations: list[dict[str, Any]],
    conversation_key: str,
    channel: str,
    message_ts: str,
    thread_ts: str,
) -> list[dict[str, Any]]:
    """Create Slack blocks with feedback buttons"""
    # Create compact feedback payload for button actions
    feedback_data = {"ck": conversation_key, "ch": channel, "mt": message_ts}
    if thread_ts:  # Only include thread_ts for channel threads, not DMs
        feedback_data["tt"] = thread_ts
    feedback_value = json.dumps(feedback_data, separators=(",", ":"))

    # Main response block
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": response_text}},
    ]
    action_elements = []

    # Citation buttons
    if citations is None or len(citations) == 0:
        logger.info("No citations")
    else:
        for i, citation in enumerate(citations):
            # Extract the first retrieved reference for this citation
            retrieved_refs = citation.get("retrievedReferences", [])
            first_ref = retrieved_refs[0] if retrieved_refs else {}

            title = first_ref.get("metadata", {}).get("title") or "Source"
            body = (
                first_ref.get("content", {}).get("text")
                or citation.get("generatedResponsePart", {}).get("textResponsePart", {}).get("text")
                or "No citation text available."
            )

            title_trunc = title[:100]
            body_trunc = body[:300]

            button = {
                "type": "button",
                "text": {"type": "plain_text", "text": title_trunc},
                "action_id": f"cite_{i}",
                "value": f"cite_{i}",
                "confirm": {
                    "title": {"type": "plain_text", "text": title_trunc},
                    "text": {"type": "mrkdwn", "text": body_trunc},
                    "confirm": {"type": "plain_text", "text": "Close"},
                    "deny": {"type": "plain_text", "text": "Cancel"},
                },
            }
            action_elements.append(button)
        blocks.append({"type": "actions", "block_id": "citation_block", "elements": action_elements})

    # Feedback buttons
    blocks.append({"type": "divider"})
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": "Was this response helpful?"}]})
    blocks.append(
        {
            "type": "actions",
            "block_id": "feedback_block",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": bot_messages.FEEDBACK_YES},
                    "action_id": "feedback_yes",
                    "value": feedback_value,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": bot_messages.FEEDBACK_NO},
                    "action_id": "feedback_no",
                    "value": feedback_value,
                },
            ],
        }
    )

    return blocks


# ================================================================
# Main async event processing
# ================================================================


def process_feedback_event(
    message_text: str,
    conversation_key: str,
    user_id: str,
    channel_id: str,
    thread_root: str,
    client: WebClient,
    event: Dict[str, Any],
) -> None:
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

        params = {"channel": channel_id, "text": bot_messages.FEEDBACK_THANKS, "thread_ts": thread_root}

        client.chat_postMessage(**params)
    except Exception as e:
        logger.error(f"Failed to post channel feedback ack: {e}", extra={"error": traceback.format_exc()})
        _, thread_ts = conversation_key_and_root(event)
        post_error_message(channel=channel_id, thread_ts=thread_ts, client=client)


def process_async_slack_action(body: Dict[str, Any], client: WebClient) -> None:
    try:
        channel_id = body["channel"]["id"]
        action_id = body["actions"][0]["action_id"]
        feedback_data = json.loads(body["actions"][0]["value"])

        # Check if this is the latest message in the conversation
        conversation_key = feedback_data["ck"]
        message_ts = feedback_data.get("mt")

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
            client.chat_postMessage(
                channel=feedback_data["ch"], text=response_message, thread_ts=feedback_data.get("tt")
            )
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


def process_async_slack_event(event: Dict[str, Any], event_id: str, client: WebClient) -> None:
    logger.debug("Processing async Slack event", extra={"event_id": event_id, "event": event})
    original_message_text = (event.get("text") or "").strip()
    message_text = strip_mentions(message_text=original_message_text)
    conversation_key, thread_ts = conversation_key_and_root(event)
    user_id = event.get("user", "unknown")
    channel_id = event["channel"]
    conversation_key, thread_root = conversation_key_and_root(event=event)
    if message_text.lower().startswith(constants.PULL_REQUEST_PREFIX):
        try:
            pull_request_id, _ = extract_pull_request_id(text=message_text)
            forward_event_to_pull_request_lambda(
                pull_request_id=pull_request_id, event=event, event_id=event_id, store_pull_request_id=True
            )
        except Exception as e:
            logger.error(f"Can not find pull request details: {e}", extra={"error": traceback.format_exc()})
            post_error_message(channel=channel_id, thread_ts=thread_ts, client=client)
        return
    if message_text.lower().startswith(constants.FEEDBACK_PREFIX):
        process_feedback_event(
            message_text=message_text,
            conversation_key=conversation_key,
            user_id=user_id,
            channel_id=channel_id,
            thread_root=thread_root,
            client=client,
            event=event,
        )
        return
    process_slack_message(event=event, event_id=event_id, client=client)


def process_slack_message(event: Dict[str, Any], event_id: str, client: WebClient) -> None:
    """
    Process Slack events asynchronously after initial acknowledgment

    This function handles the actual AI processing that takes longer than Slack's
    3-second timeout. It extracts the user query, calls Bedrock, and posts the response.
    """
    try:
        user_id = event["user"]
        channel = event["channel"]
        conversation_key, thread_ts = conversation_key_and_root(event)

        # Remove Slack user mentions from message text
        user_query = re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", event["text"]).strip()

        logger.info(
            f"Processing message from user {user_id}",
            extra={"user_query": user_query, "conversation_key": conversation_key, "event_id": event_id},
        )

        # handles empty messages
        if not user_query:
            post_params = {"channel": channel, "text": bot_messages.EMPTY_QUERY}
            if thread_ts:  # Only add thread_ts for channel threads, not DMs
                post_params["thread_ts"] = thread_ts
            client.chat_postMessage(**post_params)
            return

        # conversation continuity: reuse bedrock session across slack messages
        session_data = get_conversation_session_data(conversation_key)
        session_id = session_data.get("session_id") if session_data else None

        ai_response = process_ai_query(user_query, session_id)
        kb_response = ai_response["kb_response"]
        response_text = ai_response["text"]
        citations = ai_response["citations"]

        # Post the answer (plain) to get message_ts
        post_params = {"channel": channel, "text": response_text}
        if thread_ts:  # Only add thread_ts for channel threads, not DMs
            post_params["thread_ts"] = thread_ts
        post = client.chat_postMessage(**post_params)
        message_ts = post["ts"]

        _handle_session_management(
            conversation_key=conversation_key,
            session_data=session_data,
            session_id=session_id,
            kb_response=kb_response,
            user_id=user_id,
            channel=channel,
            thread_ts=thread_ts,
            message_ts=message_ts,
        )

        # Store Q&A pair for feedback correlation
        store_qa_pair(conversation_key, user_query, response_text, message_ts, kb_response.get("sessionId"), user_id)

        blocks = _create_feedback_blocks(response_text, citations, conversation_key, channel, message_ts, thread_ts)
        try:
            client.chat_update(channel=channel, ts=message_ts, text=response_text, blocks=blocks)
        except Exception as e:
            logger.error(
                f"Failed to attach feedback buttons: {e}",
                extra={"event_id": event_id, "message_ts": message_ts, "error": traceback.format_exc()},
            )
        log_query_stats(user_query, event, channel, client, thread_ts)
    except Exception:
        logger.error("Error processing message", extra={"event_id": event_id, "error": traceback.format_exc()})

        # Try to notify user of error via Slack
        post_error_message(channel=channel, thread_ts=thread_ts, client=client)


def process_pull_request_slack_event(slack_event_data: Dict[str, Any]) -> None:
    # separate function to process pull requests so that we can ensure we store session information
    try:
        event_id = slack_event_data["event_id"]
        event = slack_event_data["event"]
        token = get_bot_token()
        client = WebClient(token=token)
        if is_duplicate_event(event_id=event_id):
            return
        process_async_slack_event(event=event, event_id=event_id, client=client)
    except Exception:
        # we cant post a reply to slack for this error as we may not have details about where to post it
        logger.error("Error processing message", extra={"event_id": event_id, "error": traceback.format_exc()})


def process_pull_request_slack_action(slack_body_data: Dict[str, Any]) -> None:
    # separate function to process pull requests so that we can ensure we store session information
    try:
        token = get_bot_token()
        client = WebClient(token=token)
        process_async_slack_action(body=slack_body_data, client=client)
    except Exception:
        # we cant post a reply to slack for this error as we may not have details about where to post it
        logger.error("Error processing message", extra={"error": traceback.format_exc()})


def log_query_stats(user_query: str, event: Dict[str, Any], channel: str, client: WebClient, thread_ts: str) -> None:
    query_length = len(user_query)
    start_time = float(event["event_ts"])
    end_time = time.time()
    duration = end_time - start_time
    is_direct_message = event.get("channel_type") == constants.CHANNEL_TYPE_IM
    friendly_channel_name = get_friendly_channel_name(channel_id=channel, client=client)
    reporting_info = {
        "query_length": query_length,
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration,
        "thread_ts": thread_ts,
        "is_direct_message": is_direct_message,
        "channel": friendly_channel_name,
    }
    logger.info("REPORTING: query_stats", extra={"reporting_info": reporting_info})


# ================================================================
# Feedback management
# ================================================================


def store_feedback(
    conversation_key: str,
    feedback_type: str,
    user_id: str,
    channel_id: str,
    client: WebClient,
    thread_ts: str | None = None,
    message_ts: str | None = None,
    feedback_text: str | None = None,
) -> None:
    """
    Store user feedback with reference to Q&A record
    """
    try:
        friendly_channel_name = get_friendly_channel_name(channel_id=channel_id, client=client)
        reporting_info = {
            "feedback_type": feedback_type,
            "feedback_text": feedback_text,
            "thread_ts": thread_ts,
            "channel": friendly_channel_name,
        }
        logger.info("REPORTING: feedback_stats", extra={"reporting_info": reporting_info})
        now = int(time.time())
        ttl = now + constants.TTL_FEEDBACK

        # Get latest bot message timestamp for feedback linking
        if not message_ts:
            message_ts = get_latest_message_ts(conversation_key=conversation_key)

        if message_ts and feedback_type in ["positive", "negative"]:
            # Per-message feedback with deduplication for button votes only
            pk = f"{constants.FEEDBACK_PREFIX_KEY}{conversation_key}#{message_ts}"
            sk = f"{constants.USER_PREFIX}{user_id}"
            condition = "attribute_not_exists(pk) AND attribute_not_exists(sk)"  # Prevent double-voting
        elif message_ts:
            # Text feedback allows multiple entries per user
            pk = f"{constants.FEEDBACK_PREFIX_KEY}{conversation_key}#{message_ts}"
            sk = f"{constants.USER_PREFIX}{user_id}{constants.NOTE_SUFFIX}{now}"
            condition = None
        else:
            # Fallback for conversation-level feedback
            pk = f"{constants.FEEDBACK_PREFIX_KEY}{conversation_key}"
            sk = f"{constants.USER_PREFIX}{user_id}{constants.NOTE_SUFFIX}{now}"
            condition = None

        feedback_item = {
            "pk": pk,
            "sk": sk,
            "conversation_key": conversation_key,
            "feedback_type": feedback_type,
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
            feedback_item["qa_ref"] = f"qa#{conversation_key}#{message_ts}"
        if feedback_text:
            feedback_item["feedback_text"] = feedback_text[:4000]

        store_state_information(item=feedback_item, condition=condition)

        # Mark Q&A as having received feedback to prevent deletion
        if message_ts:
            _mark_qa_feedback_received(conversation_key=conversation_key, message_ts=message_ts)

        logger.info(
            "Stored feedback",
            extra={
                "pk": pk,
                "sk": sk,
                "feedback_type": feedback_type,
                "has_qa_ref": bool(message_ts),
            },
        )

    except ClientError as e:
        logger.error(f"Error storing feedback: {e}", extra={"error": traceback.format_exc()})
        raise
    except Exception as e:
        logger.error(f"Error storing feedback: {e}", extra={"error": traceback.format_exc()})


# ================================================================
# Session management
# ================================================================


def get_conversation_session(conversation_key: str) -> str | None:
    """
    Get existing Bedrock session for this conversation
    """
    session_data = get_conversation_session_data(conversation_key=conversation_key)
    return session_data.get("session_id") if session_data else None


def get_conversation_session_data(conversation_key: str) -> Dict[str, Any]:
    """
    Get full session data for this conversation
    """
    try:
        response = get_state_information(key={"pk": conversation_key, "sk": "session"})
        if "Item" in response:
            logger.info("Found existing session", extra={"conversation_key": conversation_key})
            return response["Item"]
        return None
    except Exception:
        logger.error("Error getting session", extra={"error": traceback.format_exc()})
        return None


def get_latest_message_ts(conversation_key: str) -> str | None:
    """
    Get latest message timestamp from session
    """
    try:
        response = get_state_information(key={"pk": conversation_key, "sk": constants.SESSION_SK})
        if "Item" in response:
            return response["Item"].get("latest_message_ts")
        return None
    except Exception:
        logger.error("Error getting latest message timestamp", extra={"error": traceback.format_exc()})
        return None


def store_conversation_session(
    conversation_key: str,
    session_id: str,
    user_id: str,
    channel_id: str,
    thread_ts: str = None,
    latest_message_ts: str = None,
) -> None:
    """
    Store new Bedrock session for conversation memory
    """
    try:
        ttl = int(time.time()) + constants.TTL_SESSION
        item = {
            "pk": conversation_key,
            "sk": constants.SESSION_SK,
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

        store_state_information(item=item)
        logger.info("Stored session", extra={"session_id": session_id, "conversation_key": conversation_key})
    except Exception:
        logger.error("Error storing session", extra={"error": traceback.format_exc()})


def update_session_latest_message(conversation_key: str, message_ts: str) -> None:
    """
    Update session with latest message timestamp
    """
    try:
        update_state_information(
            key={"pk": conversation_key, "sk": constants.SESSION_SK},
            update_expression="SET latest_message_ts = :ts",
            expression_attribute_values={":ts": message_ts},
        )
    except Exception:
        logger.error("Error updating session latest message", extra={"error": traceback.format_exc()})
