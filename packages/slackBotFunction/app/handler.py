"""
Main Lambda handler - dual-purpose function for Slack bot operations

This Lambda function serves two purposes:
1. Handles incoming Slack events (webhooks) via API Gateway
2. Processes async operations when invoked by itself to avoid timeouts
"""

from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from aws_lambda_powertools.utilities.typing import LambdaContext

from app.core.config import app, logger
from app.slack.slack_events import process_async_slack_event
from app.slack.slack_handlers import setup_handlers

# register event handlers with the app
setup_handlers(app)


@logger.inject_lambda_context(log_event=True)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Main Lambda entry point - routes between Slack webhook and async processing

    Flow:
    1. Slack sends webhook -> API Gateway -> Lambda (sync, 3s timeout)
    2. Lambda acknowledges immediately and triggers async self-invocation
    3. Async invocation processes Bedrock query and responds to Slack
    """
    logger.info("Lambda invoked", extra={"is_async": event.get("async_processing", False)})

    # handle async processing requests
    if event.get("async_processing"):
        slack_event_data = event.get("slack_event")
        if not slack_event_data:
            logger.error("Async processing requested but no slack_event provided")
            return {"statusCode": 400}

        process_async_slack_event(slack_event_data)
        return {"statusCode": 200}

    # handle Slack webhook requests
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
