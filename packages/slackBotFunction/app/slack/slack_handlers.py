"""
Slack event handlers - handles @mentions and direct messages to the bot
"""

import time
import json
import os
import re
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from slack_sdk import WebClient
from app.slack.slack_events import store_feedback

logger = Logger(service="slackBotFunction")


def setup_handlers(app):
    """
    Register all event handlers with the Slack app
    """
    from app.config.config import bot_token

    @app.event("app_mention")
    def handle_app_mention(event, ack, body):
        """
        Handle @mentions in channels - when users mention the bot in a channel
        Acknowledges the event immediately and triggers async processing to avoid timeouts
        """
        ack()  # Acknowledge receipt to Slack within 3 seconds

        # Handle feedback messages in @mentions
        raw_text = event.get("text", "")
        # Remove bot mention and check for feedback
        clean_text = re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", raw_text).strip()
        if clean_text.lower().startswith("feedback "):
            handle_feedback_message(event, bot_token)
            return

        event_id = body.get("event_id")
        # Skip processing if event is duplicate or missing ID to prevent double responses
        if not event_id or is_duplicate_event(event_id):
            logger.info(f"Skipping duplicate or missing event: {event_id}")
            return

        user_id = event.get("user", "unknown")
        logger.info(f"Processing @mention from user {user_id}", extra={"event_id": event_id})

        # Trigger async Lambda invocation to handle Bedrock query without timeout
        trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})

    @app.event("message")
    def handle_direct_message(event, ack, body):
        """
        Handle direct messages to the bot - private 1:1 conversations
        Filters out channel messages and processes only direct messages
        """
        ack()  # Acknowledge receipt to Slack within 3 seconds

        # Handle feedback messages
        if event.get("text", "").lower().startswith("feedback "):
            handle_feedback_message(event, bot_token)
            return

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

    @app.action("feedback_yes")
    def handle_feedback_yes(ack, body, client):
        """Handle Yes button clicks - store positive feedback and acknowledge"""
        ack()  # Acknowledge button click to Slack

        # Extract user ID and parse button value (conversation_key|original_question)
        user_id = body["user"]["id"]
        conversation_key, user_query = body["actions"][0]["value"].split("|", 1)

        # Store positive feedback linked to original question
        store_feedback(conversation_key, user_query, "positive", user_id)

        # Reply with thank you message in same thread
        client.chat_postMessage(
            channel=body["channel"]["id"], text="Thank you for your feedback!", thread_ts=body["message"]["ts"]
        )

    @app.action("feedback_no")
    def handle_feedback_no(ack, body, client):
        """Handle No button clicks - store negative feedback and prompt for details"""
        ack()  # Acknowledge button click to Slack

        # Extract user ID and parse button value (conversation_key|original_question)
        user_id = body["user"]["id"]
        conversation_key, user_query = body["actions"][0]["value"].split("|", 1)

        # Store negative feedback linked to original question
        store_feedback(conversation_key, user_query, "negative", user_id)

        # Reply with thank you and prompt for detailed feedback
        client.chat_postMessage(
            channel=body["channel"]["id"],
            text="Thank you for your feedback! Please type 'feedback' followed by your suggestions to help us improve.",
            thread_ts=body["message"]["ts"],
        )


def handle_feedback_message(event, bot_token):
    """Handle 'feedback [text]' messages - store detailed user suggestions"""
    raw_text = event["text"]
    # Remove bot mention tags and extract feedback text
    clean_text = re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", raw_text).strip()
    feedback_text = clean_text[9:].strip()  # Remove "feedback " prefix

    if feedback_text:
        # Store additional feedback with general conversation key
        # Uses "general#{channel}" since this isn't linked to specific AI response
        store_feedback(f"general#{event['channel']}", "Additional feedback", "additional", event["user"], feedback_text)

        # Send acknowledgment message
        client = WebClient(token=bot_token)
        thread_ts = event.get("thread_ts")  # Reply in thread if it's a threaded message
        client.chat_postMessage(
            channel=event["channel"],
            text="Thank you for your feedback.",
            thread_ts=thread_ts,
        )


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
