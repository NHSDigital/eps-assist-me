"""
Main Lambda handler - dual-purpose function for Slack bot operations

This Lambda function serves two purposes:
1. Handles incoming Slack events (webhooks) via API Gateway
2. Processes async operations when invoked by itself to avoid timeouts
"""

from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from app.config.config import app
from app.slack.slack_events import process_async_slack_event
from app.slack.slack_handlers import setup_handlers

# Register Slack event handlers (@mentions, DMs, etc.)
setup_handlers(app)

logger = Logger(service="slackBotFunction")


@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Main Lambda entry point - routes between Slack webhook and async processing

    Flow:
    1. Slack sends webhook -> API Gateway -> Lambda (sync, 3s timeout)
    2. Lambda acknowledges immediately and triggers async self-invocation
    3. Async invocation processes Bedrock query and responds to Slack
    """
    logger.info("Lambda invoked for Slack bot", extra={"event": event})

    # Route 2: Async processing path (self-invoked)
    if event.get("async_processing"):
        # Process the actual AI query without time constraints
        process_async_slack_event(event["slack_event"])
        return {"statusCode": 200}

    # Route 1: Slack webhook path (via API Gateway)
    # Handle initial Slack event, acknowledge quickly, trigger async processing
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
