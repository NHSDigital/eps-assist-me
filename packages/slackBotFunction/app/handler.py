"""
Main entry point for the Slack Bot Lambda Function

This is the Lambda handler that coordinates all the components, it handles both regular Slack webhooks
and async processing requests
"""

from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from aws_lambda_powertools.utilities.typing import LambdaContext

from app.core.config import app, logger
from app.slack.slack_events import process_async_slack_event
from app.slack.slack_handlers import setup_handlers

# register event handlers with the app
setup_handlers(app)


def handler(event: dict, context: LambdaContext) -> dict:
    """
    Main Lambda handler - handles Slack webhooks and async processing

    Two modes:
    1. Slack webhook -> acknowledge quickly, trigger async processing
    2. Async processing -> handle the conversation (query Bedrock, respond)
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
