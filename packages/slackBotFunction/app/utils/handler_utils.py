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


def forward_event_to_pull_request_lambda(
    pull_request_id: str, event: Dict[str, Any], event_id: str, store_pull_request_id: bool
) -> None:
    lambda_client: LambdaClient = boto3.client("lambda")
    try:
        pull_request_lambda_arn = get_pull_request_lambda_arn(pull_request_id=pull_request_id)
        # strip pull request prefix and id from message text
        message_text = event["text"]
        _, extracted_message = extract_pull_request_id(message_text)
        event["text"] = extracted_message

        lambda_payload = {"pull_request_event": True, "slack_event": {"event": event, "event_id": event_id}}
        logger.debug(
            "Forwarding event to pull request lambda",
            extra={"lambda_arn": pull_request_lambda_arn, "lambda_payload": lambda_payload},
        )
        lambda_client.invoke(
            FunctionName=pull_request_lambda_arn, InvocationType="Event", Payload=json.dumps(lambda_payload)
        )
        logger.info("Triggered pull request lambda", extra={"lambda_arn": pull_request_lambda_arn})

        if store_pull_request_id:
            conversation_key, _ = conversation_key_and_root(event)
            item = {"pk": conversation_key, "sk": constants.PULL_REQUEST_SK, "pull_request_id": pull_request_id}
            store_state_information(item=item)

    except Exception as e:
        logger.error("Failed to trigger pull request lambda", extra={"error": traceback.format_exc()})
        raise e


def forward_action_to_pull_request_lambda(body: Dict[str, Any], pull_request_id: str) -> None:
    lambda_client: LambdaClient = boto3.client("lambda")
    try:
        pull_request_lambda_arn = get_pull_request_lambda_arn(pull_request_id=pull_request_id)
        lambda_payload = {"pull_request_action": True, "slack_body": body}
        logger.debug(
            "Forwarding action to pull request lambda",
            extra={"lambda_arn": pull_request_lambda_arn, "lambda_payload": lambda_payload},
        )
        lambda_client.invoke(
            FunctionName=pull_request_lambda_arn, InvocationType="Event", Payload=json.dumps(lambda_payload)
        )
        logger.info("Triggered pull request lambda", extra={"lambda_arn": pull_request_lambda_arn})

    except Exception as e:
        logger.error("Failed to forward request to pull request lambda", extra={"error": traceback.format_exc()})
        raise e


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
    # Regex: PULL_REQUEST_PREFIX + optional space + number + space + rest of text
    pattern = re.escape(constants.PULL_REQUEST_PREFIX) + r"\s*(\d+)\s+(.+)"
    match = re.match(pattern, text)
    if not match:
        logger.warning("Can not extract pull request id from text", extra={"text": text})
        return None, text
    pr_number = int(match.group(1))
    rest_text = match.group(2)
    return pr_number, rest_text


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


def should_reply_to_message(event: Dict[str, Any]) -> bool:
    """
    Determine if the bot should reply to the message.

    Conditions:
    should not reply if:
    - Message is in a group chat (channel_type == 'group') but not in a thread
    """

    if event.get("channel_type") == "group" and event.get("type") == "message" and event.get("thread_ts") is None:
        return False
    return True
