"""
Slack event processing
Handles conversation memory, Bedrock queries, and responding back to Slack
"""

import re
import time
import traceback
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
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

from app.services.sample_questions import SampleQuestionBank
from app.services.slack import get_friendly_channel_name, post_error_message
from app.utils.handler_utils import (
    conversation_key_and_root,
    extract_pull_request_id,
    extract_test_command_params,
    forward_to_pull_request_lambda,
    is_duplicate_event,
    is_latest_message,
    strip_mentions,
)

from app.services.ai_processor import process_ai_query


logger = get_logger()

processing_error_message = "Error processing message"


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
    citations: list[dict[str, str]],
    feedback_data: dict[str, str],
) -> list[dict[str, Any]]:
    """Create Slack blocks with feedback buttons"""
    if feedback_data.get("thread_ts"):  # Only include thread_ts for channel threads, not DMs
        feedback_data["tt"] = feedback_data["thread_ts"]
    feedback_value = json.dumps(feedback_data, separators=(",", ":"))

    # Main response block
    blocks = _create_response_body(citations, feedback_data, response_text)

    # Feedback buttons
    blocks.append({"type": "divider", "block_id": "feedback-divider"})
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

    logger.info("Blocks", extra={"blocks": blocks})
    return blocks


def _create_response_body(citations: list[dict[str, str]], feedback_data: dict[str, str], response_text: str):
    blocks = []
    action_buttons = []

    # Create citation buttons
    if citations is None or len(citations) == 0:
        logger.info("No citations")
    else:
        for i, citation in enumerate(citations):
            result = _create_citation(citation, feedback_data, response_text)

            action_buttons += result.get("action_buttons", [])
            response_text = result.get("response_text", response_text)

    # Remove any citations that have not been returned
    response_text = convert_markdown_to_slack(response_text)
    response_text = response_text.replace("cit_", "")

    # Main body
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": response_text}})

    # Citation action block
    if action_buttons:
        blocks.append(
            {
                "type": "actions",
                "block_id": "citation_actions",
                "elements": action_buttons,
            }
        )

    return blocks


def _create_citation(citation: dict[str, str], feedback_data: dict, response_text: str):
    invalid_body = "No document excerpt available."
    action_buttons = []

    # Create citation blocks ["source_number", "title", "excerpt", "relevance_score"]
    source_number: str = (citation.get("source_number", "0")).replace("\n", "")
    title: str = citation.get("title") or citation.get("filename") or "Source"
    body: str = citation.get("excerpt") or invalid_body
    score: float = float(citation.get("relevance_score") or "0")

    # Format body
    body = convert_markdown_to_slack(body)

    if score < 0.6:  # low relevance score, skip citation
        logger.info("Skipping low relevance citation", extra={"source_number": source_number, "score": score})
    else:
        # Buttons can only be 75 characters long, truncate to be safe
        button_text = f"[{source_number}] {title}"
        button_value = {**feedback_data, "source_number": source_number, "title": title, "body": body, "score": score}
        button = {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": button_text if len(button_text) < 75 else f"{button_text[:70]}...",
            },
            "action_id": f"cite_{source_number}",
            "value": json.dumps(
                button_value,
                separators=(",", ":"),
            ),
        }
        action_buttons.append(button)

        # Update inline citations to remove "cit_" prefix
        response_text = response_text.replace(f"[cit_{source_number}]", f"[{source_number}]")
        logger.info("Created citation", extra=button_value)

    return {"action_buttons": action_buttons, "response_text": response_text}


def convert_markdown_to_slack(body: str) -> str:
    """Convert basic markdown to Slack formatting"""
    if not body:
        return ""

    # 1. Fix common encoding issues
    body = body.replace("»", "")
    body = body.replace("â¢", "-")

    # 2. Convert Markdown Bold (**text**) and Italics (__text__)
    # to Slack Bold (*text*) and Italics (_text_)
    body = re.sub(r"([\*_]){2,10}([^*]+)([\*_]){2,10}", r"\1\2\1", body)

    # 3. Handle Lists (Handle various bullet points and dashes, inc. unicode support)
    body = re.sub(r"(?:^|\s{1,10})[-•–—▪‣◦⁃]\s{0,10}", r"\n- ", body)

    # 4. Convert Markdown Links [text](url) to Slack <url|text>
    body = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"<\2|\1>", body)

    return body.strip()


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
    logger.info("Processing slack action", extra={"body": body})
    try:
        # Extract necessary information from the action payload
        message = body[
            "message"
        ]  # The original message object is sent back on an action, so we don't need to fetch it again
        action = body["actions"][0]
        action_id = action["action_id"]
        action_data = json.loads(action["value"])

        # Check if this is the latest message in the conversation
        conversation_key = action_data["ck"]
        message_ts = action_data["mt"]

        # Required for updating
        channel_id = body["channel"]["id"]
        timestamp = body["message"]["ts"]

        # Check if the action is for a citation (safely)
        if str(action_id or "").startswith("cite"):
            # Update message to include citation content
            open_citation(channel_id, timestamp, message, action_data, client)
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
                conversation_key=action_data["ck"],
                feedback_type=feedback_type,
                user_id=body["user"]["id"],
                channel_id=action_data["ch"],
                thread_ts=action_data.get("tt"),
                message_ts=action_data.get("mt"),
                client=client,
            )
            # Only post message if storage succeeded
            client.chat_postMessage(channel=action_data["ch"], text=response_message, thread_ts=action_data.get("tt"))
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                # Silently ignore duplicate votes - user already voted on this message
                logger.info(f"Duplicate vote ignored for user {body['user']['id']}")
                return
            logger.error(f"Feedback storage error: {e}", extra={"error": traceback.format_exc()})
        except Exception as e:
            logger.error(f"Unexpected feedback error: {e}", extra={"error": traceback.format_exc()})
            thread_ts = action_data.get("tt")
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
            forward_to_pull_request_lambda(
                body={},
                pull_request_id=pull_request_id,
                event=event,
                event_id=event_id,
                store_pull_request_id=True,
                type="event",
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


def process_async_slack_command(command: Dict[str, Any], client: WebClient) -> None:
    logger.debug("Processing async Slack command", extra={"command": command})

    try:
        command_arg = command.get("command", "").strip()
        if command_arg == "/test":
            process_command_test_request(command=command, client=client)
    except Exception as e:
        logger.error(f"Error processing test command: {e}", extra={"error": traceback.format_exc()})
        post_error_message(channel=command["channel_id"], thread_ts=None, client=client)


# ================================================================
# Pull Request Re-routing
# ================================================================


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
        logger.error(processing_error_message, extra={"event_id": event_id, "error": traceback.format_exc()})


def process_pull_request_slack_command(slack_command_data: Dict[str, Any]) -> None:
    # separate function to process pull requests so that we can ensure we store session information
    logger.debug(
        "Processing pull request slack command", extra={"slack_command_data": slack_command_data}
    )  # Removed line after debugging
    try:
        command = slack_command_data["event"]
        token = get_bot_token()
        client = WebClient(token=token)
        process_async_slack_command(command=command, client=client)
    except Exception:
        # we cant post a reply to slack for this error as we may not have details about where to post it
        logger.error(processing_error_message, extra={"error": traceback.format_exc()})


def process_pull_request_slack_action(slack_body_data: Dict[str, Any]) -> None:
    # separate function to process pull requests so that we can ensure we store session information
    try:
        token = get_bot_token()
        client = WebClient(token=token)
        process_async_slack_action(body=slack_body_data, client=client)
    except Exception:
        # we cant post a reply to slack for this error as we may not have details about where to post it
        logger.error(processing_error_message, extra={"error": traceback.format_exc()})


# ================================================================
# Slack Message management
# ================================================================


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

        # Post the answer (plain) to get message_ts
        post_params = {"channel": channel, "text": "Processing..."}
        if thread_ts:  # Only add thread_ts for channel threads, not DMs
            post_params["thread_ts"] = thread_ts
        post = client.chat_postMessage(**post_params)
        message_ts = post["ts"]

        # Create compact feedback payload for button actions
        feedback_data = {"channel": channel, "message_ts": message_ts, "thread_ts": thread_ts}

        # Call Bedrock to process the user query
        kb_response, response_text, blocks = process_formatted_bedrock_query(
            user_query=user_query, session_id=session_id, feedback_data={**feedback_data, "ck": conversation_key}
        )

        _handle_session_management(
            **feedback_data,
            session_data=session_data,
            session_id=session_id,
            kb_response=kb_response,
            user_id=user_id,
            conversation_key=conversation_key,
        )

        # Store Q&A pair for feedback correlation
        store_qa_pair(conversation_key, user_query, response_text, message_ts, kb_response.get("sessionId"), user_id)

        try:
            client.chat_update(channel=channel, ts=message_ts, text=response_text, blocks=blocks)
        except Exception as e:
            logger.error(
                f"Failed to update message: {e}",
                extra={"event_id": event_id, "message_ts": message_ts, "error": traceback.format_exc()},
            )
        log_query_stats(user_query, event, channel, client, thread_ts)
    except Exception as e:
        logger.error(f"Error processing message: {e}", extra={"event_id": event_id, "error": traceback.format_exc()})

        # Try to notify user of error via Slack
        post_error_message(channel=channel, thread_ts=thread_ts, client=client)


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
# Slack Feedback management
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
# AI Response Formatting
# ================================================================


def process_formatted_bedrock_query(
    user_query: str, session_id: str | None, feedback_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Process the user query with Bedrock and return the response dict"""
    ai_response = process_ai_query(user_query, session_id)
    kb_response = ai_response["kb_response"]
    response_text = ai_response["text"]

    # Split out citation block if present
    # Citations are not returned in the object without using `$output_format_instructions$` which overrides the
    # system prompt. Instead, pull out and format the citations in the prompt manually
    prompt_value_keys = ["source_number", "title", "excerpt", "relevance_score"]
    split = response_text.split("------")  # Citations are separated from main body by ------

    citations: list[dict[str, str]] = []
    if len(split) != 1:
        response_text = split[0]
        citation_block = split[1]
        raw_citations = []
        raw_citations = re.compile(r"<cit\b[^>]*>(.*?)</cit>", re.DOTALL | re.IGNORECASE).findall(citation_block)
        if len(raw_citations) > 0:
            logger.info("Found citation(s)", extra={"Raw Citations": raw_citations})
            citations = [dict(zip(prompt_value_keys, citation.split("||"))) for citation in raw_citations]
    logger.info("Parsed citation(s)", extra={"citations": citations})

    blocks = _create_feedback_blocks(response_text, citations, feedback_data)

    return kb_response, response_text, blocks


def open_citation(channel: str, timestamp: str, message: Any, params: Dict[str, Any], client: WebClient) -> None:
    """Open citation - update/replace message to include citation content"""
    logger.info("Opening citation", extra={"channel": channel, "timestamp": timestamp})
    try:
        # Citation details
        title: str = params.get("title", "No title available.").strip()
        body: str = params.get("body", "No citation text available.").strip()
        source_number: str = params.get("source_number")

        # Remove any existing citation block/divider
        blocks = message.get("blocks", [])
        blocks = [b for b in blocks if b.get("block_id") not in ["citation_block", "citation_divider"]]

        # Format text
        title = f"*{title.replace('\n', '')}*"
        if body and len(body) > 0:
            body = f"> {body.replace('\n', '\n> ')}"  # Block quote
            body = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"<\1|\2>", body)  # Convert links
            body = body.replace("»", "")  # Remove double chevrons

        current_id = f"cite_{source_number}".strip()

        # Reset all button styles, then set the clicked one
        result = format_blocks(blocks, current_id)
        selected = result["selected"]
        blocks = result["blocks"]

        # If selected, insert citation block before feedback
        if selected:
            citation_block = {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{title}\n\n{body}"},
                "block_id": "citation_block",
            }
            feedback_index = next(
                (i for i, b in enumerate(blocks) if b.get("block_id") == "feedback-divider"),
                len(blocks),
            )
            blocks.insert(feedback_index, citation_block)

        # Update Slack message
        logger.info("Updated message body", extra={"blocks": blocks})
        client.chat_update(channel=channel, ts=timestamp, blocks=blocks)

    except Exception as e:
        logger.error(f"Error updating message for citation: {e}", extra={"error": traceback.format_exc()})


def format_blocks(blocks: Any, current_id: str):
    """Format blocks by styling the selected citation button and unstyle others"""
    selected = False

    for block in blocks:
        if block.get("type") != "actions":
            continue

        for element in block.get("elements", []):
            if element.get("type") != "button":
                continue

            if element.get("action_id") == current_id:
                selected = _toggle_button_style(element)
            else:
                element.pop("style", None)

    return {"selected": selected, "blocks": blocks}


def _toggle_button_style(element: dict) -> bool:
    """Toggle button style and return whether it's now selected"""
    if element.get("style") == "primary":
        element.pop("style", None)
        return False
    else:
        element["style"] = "primary"
        return True


# ================================================================
# Slack Command management
# ================================================================


def process_command_test_request(command: Dict[str, Any], client: WebClient) -> None:
    if "help" in command.get("text"):
        process_command_test_help(command=command, client=client)
    else:
        process_command_test_questions(command=command, client=client)


def process_command_test_questions(command: Dict[str, Any], client: WebClient) -> None:
    # Prepare response

    try:
        acknowledgement_msg = f"<@{command.get("user_id")}> has initiated testing."
        logger.info(acknowledgement_msg, extra={"command": command})

        # Extract parameters
        params = extract_test_command_params(command.get("text"))

        # Is the command targeting a PR
        pr = params.get("pr", "").strip()
        if pr:
            pr = f"pr: {pr}"
            acknowledgement_msg += f" for {pr}\n"

        # Initial acknowledgment
        post_params = {
            "channel": command["channel_id"],
            "text": acknowledgement_msg,
        }
        client.chat_postMessage(**post_params)

        # Has the user defined any questions
        start = int(params.get("start", 1))
        end = int(params.get("end", 22))
        acknowledgement_msg = f"Loading {f"questions {start} to {end}" if end != start else f"question {start}"}"

        # Should the answer be output to the channel
        output = params.get("output", False)
        logger.info("Test command parameters", extra={"pr": pr, "start": start, "end": end})
        acknowledgement_msg += " and printing results to channel" if output else ""

        # Post query information (for reflection in future)
        post_params = {
            "channel": command["channel_id"],
            "text": acknowledgement_msg,
        }
        client.chat_postEphemeral(**post_params, user=command.get("user_id"))

        # Retrieve sample questions
        test_questions = SampleQuestionBank().get_questions(start=start - 1, end=end - 1)
        logger.info("Retrieved test questions", extra={"count": len(test_questions)})

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []

            for question in test_questions:
                # This happens sequentially, ensuring questions appear 1, 2, 3...
                response = {}
                if output:
                    post_params["text"] = f"Question {question[0]}:\n> {question[1].replace('\n', '\n> ')}\n"
                    response = client.chat_postMessage(**post_params)

                # We submit the work to the pool. It starts immediately.
                future = executor.submit(
                    process_command_test_ai_request,
                    question=question,
                    response=response,  # Pass the response object we just got
                    output=output,
                    client=client,
                )
                futures.append(future)

        post_params["text"] = "Testing complete, generating file..."
        client.chat_postEphemeral(**post_params, user=command.get("user_id"))

        aggregated_results = []
        for i, future in enumerate(futures):
            try:
                question = future.result()
                aggregated_results.append(f"# Question {question.get("index", i)}:")
                aggregated_results.append(f"{question.get("text", "").strip()}\n")
                aggregated_results.append(f"# Response:\n{question.get("response", "").strip()}")
            except Exception as e:
                aggregated_results.append(f"**[Q{i}] Error processing request**: {str(e)}")
            aggregated_results.append("\n---\n")

        # Create the file content
        name_timestamp = datetime.now().strftime("%y%m%d%M%H")

        filename = f"EpsamTestResults_{name_timestamp}_.txt"
        final_file_content = "\n".join(aggregated_results)

        # Upload the file to Slack
        client.files_upload_v2(
            channel=command["channel_id"],
            content=final_file_content,
            title=filename,
            filename=filename,
            snippet_type="markdown",
            initial_comment="Here are your results:",
        )
    except Exception as e:
        logger.error(
            f"Failed to attach feedback buttons: {e}",
            extra={"channel": command["channel_id"], "error": traceback.format_exc()},
        )


def process_command_test_ai_request(question, response, output: bool, client: WebClient) -> dict[str, str]:
    logger.debug("Processing test question", extra={"question": question})

    message_ts = response.get("ts")
    channel = response.get("channel")

    feedback_data = {
        "ck": None,
        "ch": channel,
        "mt": message_ts,
        "thread_ts": message_ts,
    }

    _, response_text, blocks = process_formatted_bedrock_query(question[1], None, feedback_data)
    logger.debug("question complete", extra={"response_text": response_text, "blocks": blocks})

    if output:
        try:
            client.chat_postMessage(channel=channel, thread_ts=message_ts, text=response_text, blocks=blocks)
        except Exception as e:
            logger.error(
                f"Failed to attach feedback buttons: {e}",
                extra={"event_id": None, "message_ts": message_ts, "error": traceback.format_exc()},
            )

    return {"index": question[0], "text": question[1], "response": response_text}


def process_command_test_help(command: Dict[str, Any], client: WebClient) -> None:
    logger.info("Processing Command Test Help Message", extra={"command": command})
    length = SampleQuestionBank().length() + 1
    help_text = f"""
    Certainly! Here is some help testing me!

    You can use the `/test` command to send sample test questions to the bot.
    Once the test is complete, the bot will respond with a text file to view the results.

    - Usage:
       - /test [q<start_index>-<end_index>] [.<output>]

    - Parameters:
       - <start_index>: (optional) The starting and ending index of the sample questions (default is 1-{length}).
       - <end-index>: (optional) The ending index of the sample questions (default is {length}).
       - <output> (optional) If provided, will post questions and answers to slack (this won't effect if the file is returned)

    - Examples:
        - /test --> Sends questions 1 to {length}
        - /test q15 --> Sends question 15 only
        - /test q10-16 --> Sends questions 10 to 16
        - /test .output -> Sends questions 1 to {length} and posts them to Slack
    """  # noqa: E501
    client.chat_postEphemeral(channel=command["channel_id"], user=command["user_id"], text=help_text)


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
