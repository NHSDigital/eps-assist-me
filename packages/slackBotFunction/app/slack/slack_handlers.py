"""
Slack event handlers - handles @mentions and direct messages to the bot
"""

import time
import json
import traceback
import boto3
from botocore.exceptions import ClientError
from app.core.config import table, bot_token, logger
import os


def setup_handlers(app):
    """
    Register all event handlers with the Slack app
    """

    @app.middleware
    def log_request(slack_logger, body, next):
        logger.debug("Slack request received", extra={"body": body})
        return next()

    @app.event("app_mention")
    def handle_app_mention(event, ack, body):
        """
        Handle @mentions in channels - when users mention the bot in a channel
        Acknowledges the event immediately and triggers async processing to avoid timeouts
        """
        ack()

        event_id = body.get("event_id")
        if not event_id or is_duplicate_event(event_id):
            logger.info("Skipping duplicate or missing event", extra={"event_id": event_id})
            return

        user_id = event.get("user", "unknown")
        logger.info("Processing @mention from user", extra={"user_id": user_id, "event_id": event_id})

        trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})

    @app.event("message")
    def handle_direct_message(event, ack, body):
        """
        Handle direct messages to the bot - private 1:1 conversations
        Filters out channel messages and processes only direct messages
        """
        ack()

        # Only handle DMs, ignore channel messages
        if event.get("channel_type") != "im":
            return

        event_id = body.get("event_id")
        if not event_id or is_duplicate_event(event_id):
            logger.info("Skipping duplicate or missing event", extra={"event_id": event_id})
            return

        user_id = event.get("user", "unknown")
        logger.info("Processing DM from user", extra={"user_id": user_id, "event_id": event_id})

        trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})


def is_duplicate_event(event_id):
    """
    Check if we've already processed this event using DynamoDB conditional writes

    Slack may send duplicate events due to retries, so we use DynamoDB's
    conditional write to atomically check and record event processing.
    """
    try:
        ttl = int(time.time()) + 3600  # 1 hour TTL
        table.put_item(
            Item={"pk": f"event#{event_id}", "sk": "dedup", "ttl": ttl, "timestamp": int(time.time())},
            ConditionExpression="attribute_not_exists(pk)",
        )
        return False  # Not a duplicate
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return True  # Duplicate
        logger.error("Error checking event duplication", extra={"error": traceback.format_exc()})
        return False


def trigger_async_processing(event_data):
    """
    Trigger asynchronous Lambda invocation to process Slack events

    Slack requires responses within 3 seconds, but Bedrock queries can take longer.
    This function invokes the same Lambda function asynchronously to handle the
    actual AI processing without blocking the initial Slack response.
    """
    # incase we fail to re-invoke the lambda we should log an error
    try:
        lambda_client = boto3.client("lambda")
        lambda_client.invoke(
            FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"],
            InvocationType="Event",
            Payload=json.dumps({"async_processing": True, "slack_event": event_data}),
        )
        logger.info("Async processing triggered successfully")
    except Exception:
        logger.error("Failed to trigger async processing", extra={"error": traceback.format_exc()})
