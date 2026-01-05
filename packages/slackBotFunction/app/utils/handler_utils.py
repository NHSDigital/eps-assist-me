"""
Slack event handlers - handles @mentions and direct messages to the bot
"""

import re
import time
import json
import traceback
from typing import Any, Dict, Tuple
import boto3
from botocore.exceptions import ClientError
from slack_sdk import WebClient
from mypy_boto3_cloudformation.client import CloudFormationClient
from mypy_boto3_lambda.client import LambdaClient

from app.services.dynamo import get_state_information, store_state_information
from app.core.config import (
    get_logger,
    constants,
)

logger = get_logger()


def is_duplicate_event(event_id: str) -> bool:
    """
    Check if we've already processed this event using DynamoDB conditional writes

    Slack may send duplicate events due to retries, so we use DynamoDB's
    conditional write to atomically check and record event processing.
    """
    try:
        ttl = int(time.time()) + 3600  # 1 hour TTL
        store_state_information(
            {"pk": f"event#{event_id}", "sk": "dedup", "ttl": ttl, "timestamp": int(time.time())},
            "attribute_not_exists(pk)",
        )
        return False  # Not a duplicate
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.info(f"Duplicate event detected: {event_id}")
            return True  # Duplicate
        logger.error("Error checking event duplication", extra={"error": traceback.format_exc()})
        return False


def respond_with_eyes(event: Dict[str, Any], client: WebClient) -> None:
    channel = event["channel"]
    ts = event["ts"]
    try:
        logger.debug("Responding with eyes")
        client.reactions_add(channel=channel, timestamp=ts, name="eyes")
    except Exception:
        logger.warning("Failed to respond with eyes", extra={"error": traceback.format_exc()})


def get_pull_request_lambda_arn(pull_request_id: str) -> str:
    cloudformation_client: CloudFormationClient = boto3.client("cloudformation")
    try:
        logger.debug("Getting arn for pull request", extra={"pull_request_id": pull_request_id})
        response = cloudformation_client.describe_stacks(StackName=f"epsam-pr-{pull_request_id}")
        outputs = {o["OutputKey"]: o["OutputValue"] for o in response["Stacks"][0]["Outputs"]}
        pull_request_lambda_arn = outputs.get("SlackBotLambdaArn")
        return pull_request_lambda_arn
    except Exception as e:
        logger.error("Failed to get pull request lambda arn", extra={"error": traceback.format_exc()})
        raise e


def forward_to_pull_request_lambda(
    body: Dict[str, Any],
    event: Dict[str, Any],
    event_id: str,
    pull_request_id: str,
    store_pull_request_id: bool,
    type: str,
) -> None:
    lambda_client: LambdaClient = boto3.client("lambda")
    try:
        pull_request_lambda_arn = get_pull_request_lambda_arn(pull_request_id=pull_request_id)
        lambda_payload = get_forward_payload(body=body, event=event, event_id=event_id, type=type)
        logger.debug(
            f"Forwarding '{type}' to pull request lambda",
            extra={"lambda_arn": pull_request_lambda_arn, "lambda_payload": lambda_payload},
        )
        lambda_client.invoke(
            FunctionName=pull_request_lambda_arn, InvocationType=type.title(), Payload=json.dumps(lambda_payload)
        )
        logger.info("Triggered pull request lambda", extra={"lambda_arn": pull_request_lambda_arn})

        if store_pull_request_id:
            conversation_key, _ = conversation_key_and_root(event)
            item = {"pk": conversation_key, "sk": constants.PULL_REQUEST_SK, "pull_request_id": pull_request_id}
            store_state_information(item=item)

    except Exception as e:
        logger.error("Failed to forward request to pull request lambda", extra={"error": traceback.format_exc()})
        raise e


def get_forward_payload(body: Dict[str, Any], event: Dict[str, Any], event_id: str, type: str) -> Dict[str, Any]:
    if type != "event":
        return {f"pull_request_{type}": True, "slack_body": body}

    if event_id is None or event["text"] is None:
        logger.error("Missing required fields to forward pull request event")
        return None

    message_text = event["text"]
    _, extracted_message = extract_pull_request_id(message_text)
    event["text"] = extracted_message
    return {"pull_request_event": True, "slack_event": {"event": event, "event_id": event_id}}


def is_latest_message(conversation_key: str, message_ts: str) -> bool:
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


def gate_common(event: Dict[str, Any], body: Dict[str, Any]) -> str | None:
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


def strip_mentions(message_text: str) -> str:
    """Remove Slack user mentions like <@U123> or <@U123|alias> from text."""
    return re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", message_text or "").strip()


def extract_pull_request_id(text: str) -> Tuple[str | None, str]:
    prefix = re.escape(constants.PULL_REQUEST_PREFIX)  # safely escape for regex
    pattern = rf"^(<[^>]+>\s*)?{prefix}\s*(\d+)\b"

    match = re.match(pattern, text, flags=re.IGNORECASE)
    if match:
        mention = match.group(1) or ""
        pr_number = match.group(2)

        # Remove the matched part (mention + prefix + number)
        remaining_text = text[match.end() :].strip()
        cleaned_text = f"{mention}{remaining_text}".strip()
        return pr_number, cleaned_text

    return None, text.strip()


def extract_test_command_params(text: str) -> Dict[str, str]:
    """
    Extract parameters from the /test command text.

    Expected format: /test pr: 123 q1-2
    """
    params = {
        "pr": "",
        "start": "0",
        "end": "20",
    }
    prefix = re.escape(constants.PULL_REQUEST_PREFIX)  # safely escape for regex
    pr_pattern = rf"{prefix}\s*(\d+)\b"
    q_pattern = r"\bq-?(\d+)(?:-(\d+))?"

    pr_match = re.match(pr_pattern, text, flags=re.IGNORECASE)
    if pr_match:
        params["pr"] = pr_match.group(1)

    q_match = re.search(q_pattern, text, flags=re.IGNORECASE)
    if q_match:
        params["start"] = q_match.group(1)
        params["end"] = q_match.group(2) if q_match.group(2) else q_match.group(1)

    logger.debug("Extracted test command parameters", extra={"params": params})
    return params


def conversation_key_and_root(event: Dict[str, Any]) -> Tuple[str, str]:
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
        return f"{constants.DM_PREFIX}{channel_id}#{root}", root
    return f"{constants.THREAD_PREFIX}{channel_id}#{root}", root


def extract_session_pull_request_id(conversation_key: str) -> str | None:
    """Check if the conversation is associated with a pull request"""
    logger.debug("Checking for existing pull request session", extra={"conversation_key": conversation_key})
    try:
        response = get_state_information({"pk": conversation_key, "sk": constants.PULL_REQUEST_SK})
        if "Item" in response:
            logger.info("Found existing pull request session", extra={"conversation_key": conversation_key})
            logger.debug("response", extra={"response": response})
            return response["Item"]["pull_request_id"]
        return None
    except Exception as e:
        logger.error(f"Error checking pull request session: {e}", extra={"error": traceback.format_exc()})
        return None


def get_bot_user_id(client: WebClient) -> str | None:
    """
    Get the bot's user ID using auth.test API.
    This is cached to avoid repeated API calls.
    """
    if not hasattr(get_bot_user_id, "_cache"):
        get_bot_user_id._cache = {}

    cache_key = id(client)

    if cache_key in get_bot_user_id._cache:
        return get_bot_user_id._cache[cache_key]

    try:
        auth_response = client.auth_test()
        if auth_response.get("ok"):
            bot_user_id = auth_response.get("user_id")
            get_bot_user_id._cache[cache_key] = bot_user_id
            logger.info("Cached bot user ID", extra={"bot_user_id": bot_user_id})
            return bot_user_id
    except Exception:
        logger.error("Error fetching bot user ID", extra={"error": traceback.format_exc()})

    return None


def was_bot_mentioned_in_thread_root(channel: str, thread_ts: str, client: WebClient) -> bool:
    """
    Check if THIS specific bot was mentioned anywhere in the thread history.
    This handles cases where:
    - Multiple bots are in the same channel (checks for this bot's specific user ID)
    - Bot is mentioned later in a thread (not just the root message)
    """
    try:
        # get this bot's user ID
        bot_user_id = get_bot_user_id(client)
        if not bot_user_id:
            logger.warning("Could not determine bot user ID, failing open")
            return True

        response = client.conversations_replies(channel=channel, ts=thread_ts, inclusive=True)

        if not response.get("ok") or not response.get("messages"):
            logger.warning("Failed to fetch thread messages", extra={"channel": channel, "thread_ts": thread_ts})
            return True

        # check if THIS bot is mentioned in any message in the thread
        bot_mention_pattern = rf"<@{re.escape(bot_user_id)}(?:\|[^>]+)?>"

        for message in response["messages"]:
            message_text = message.get("text", "")
            if re.search(bot_mention_pattern, message_text):
                logger.debug(
                    "Found bot mention in thread",
                    extra={
                        "channel": channel,
                        "thread_ts": thread_ts,
                        "bot_user_id": bot_user_id,
                        "message_ts": message.get("ts"),
                    },
                )
                return True

        logger.debug(
            "Bot not mentioned in thread",
            extra={"channel": channel, "thread_ts": thread_ts, "bot_user_id": bot_user_id},
        )
        return False

    except Exception:
        logger.error("Error checking bot mention in thread", extra={"error": traceback.format_exc()})
        return True


def should_reply_to_message(event: Dict[str, Any], client: WebClient = None) -> bool:
    """
    Determine if the bot should reply to the message.

    Conditions:
    should not reply if:
    - Message is in a group chat (channel_type == 'group') but not in a thread
    - Message is in a channel or group thread where the bot was not initially mentioned
    """
    logger.debug("Checking if should reply to message", extra={"event": event, "client": client})

    # we don't reply to non-threaded messages in group chats
    if event.get("channel_type") == "group" and event.get("type") == "message" and event.get("thread_ts") is None:
        return False

    # for channel or group threads, check if bot was mentioned anywhere in the thread history
    if event.get("channel_type") in ["channel", "group"] and event.get("thread_ts"):
        if not client:
            logger.warning("No Slack client provided to check thread participation")
            return True

        channel = event.get("channel")
        thread_ts = event.get("thread_ts")

        if not was_bot_mentioned_in_thread_root(channel, thread_ts, client):
            logger.debug(
                "Bot not mentioned in thread, ignoring message", extra={"channel": channel, "thread_ts": thread_ts}
            )
            return False

    return True
