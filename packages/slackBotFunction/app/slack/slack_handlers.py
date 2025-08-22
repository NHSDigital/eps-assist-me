"""
Slack event handlers - handles @mentions and direct messages to the bot
"""

import time
import json
import os
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from app.config.config import bot_token

logger = Logger(service="slackBotFunction")


def setup_handlers(app):
    """
    Configure and register all Slack event handlers and middleware with the app.

    This is the main entry point for setting up the bot's event handling capabilities.
    Called during app initialization to wire up all handlers.
    """
    app.event("app_mention")(handle_app_mention)
    app.event("message")(handle_direct_message)


def handle_app_mention(event, ack, body):
    """
    Handle @mentions in channels - when users mention the bot in a channel
    Acknowledges the event immediately and triggers async processing to avoid timeouts
    """

    ack()  # Acknowledge receipt to Slack within 3 seconds

    event_id = body.get("event_id")
    # Skip processing if event is duplicate or missing ID to prevent double responses
    if not event_id or is_duplicate_event(event_id):
        logger.info(f"Skipping duplicate or missing event: {event_id}")
        return

    user_id = event.get("user", "unknown")
    logger.info(f"Processing @mention from user {user_id}", extra={"event_id": event_id})

    # Trigger async Lambda invocation to handle Bedrock query without timeout
    trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})


def handle_direct_message(event, ack, body):
    """
    Handle direct messages to the bot - private 1:1 conversations
    Filters out channel messages and processes only direct messages
    """

    ack()  # Acknowledge receipt to Slack within 3 seconds

    # Only handle direct messages ("im" = instant message), ignore channel messages
    if event.get("channel_type") != "im":
        return

    event_id = body.get("event_id")
    # Skip processing if event is duplicate or missing ID to prevent double responses
    if not event_id or is_duplicate_event(event_id):
        logger.info(f"Skipping duplicate or missing event: {event_id}")
        return

    user_id = event.get("user", "unknown")
    logger.info(f"Processing DM from user {user_id}", extra={"event_id": event_id})

    # Trigger async Lambda invocation to handle Bedrock query without timeout
    trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})


def is_duplicate_event(event_id):
    """
    Check if we've already processed this event using DynamoDB conditional writes

    Slack may send duplicate events due to retries, so we use DynamoDB's
    conditional write to atomically check and record event processing.
    """
    from app.config.config import table

    try:
        ttl = int(time.time()) + 3600  # 1 hour TTL for automatic cleanup
        # Attempt to insert event record - fails if already exists
        table.put_item(
            Item={"eventId": event_id, "ttl": ttl, "timestamp": int(time.time())},
            ConditionExpression="attribute_not_exists(eventId)",  # Only insert if doesn't exist
        )
        return False  # Successfully inserted = not a duplicate
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return True  # Insert failed = duplicate event
        logger.error(f"Error checking event duplication: {e}")
        return False  # On error, allow processing to avoid blocking legitimate events


def trigger_async_processing(event_data):
    """
    Trigger asynchronous Lambda invocation to process Slack events

    Slack requires responses within 3 seconds, but Bedrock queries can take longer.
    This function invokes the same Lambda function asynchronously to handle the
    actual AI processing without blocking the initial Slack response.
    """
    lambda_client = boto3.client("lambda")

    # Invoke same Lambda function asynchronously ("Event" = fire-and-forget)
    lambda_client.invoke(
        FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"],
        InvocationType="Event",  # Asynchronous invocation
        Payload=json.dumps({"async_processing": True, "slack_event": event_data}),
    )
