"""
Slack event handlers - handles @mentions and DMs
"""

import time
import json
import boto3
from botocore.exceptions import ClientError
from app.core.config import table, bot_token, logger


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
        Handle @mentions in channels
        """
        ack()

        event_id = body.get("event_id")
        if not event_id or is_duplicate_event(event_id):
            logger.info(f"Skipping duplicate or missing event: {event_id}")
            return

        user_id = event.get("user", "unknown")
        logger.info(f"Processing @mention from user {user_id}", extra={"event_id": event_id})

        trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})

    @app.event("message")
    def handle_direct_message(event, ack, body):
        """
        Handle direct messages to the bot
        """
        ack()

        # Only handle DMs, ignore channel messages
        if event.get("channel_type") != "im":
            return

        event_id = body.get("event_id")
        if not event_id or is_duplicate_event(event_id):
            logger.info(f"Skipping duplicate or missing event: {event_id}")
            return

        user_id = event.get("user", "unknown")
        logger.info(f"Processing DM from user {user_id}", extra={"event_id": event_id})

        trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})


def is_duplicate_event(event_id):
    """
    Check if we've already processed this event
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
        logger.error(f"Error checking event duplication: {e}")
        return False


def trigger_async_processing(event_data):
    """Fire off async processing to avoid timeout."""
    lambda_client = boto3.client("lambda")
    import os

    lambda_client.invoke(
        FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"],
        InvocationType="Event",
        Payload=json.dumps({"async_processing": True, "slack_event": event_data}),
    )
