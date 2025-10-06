"""
Main Lambda handler - dual-purpose function for Slack bot operations

This Lambda function serves two purposes:
1. Handles incoming Slack events (webhooks) via API Gateway
2. Processes async operations when invoked by itself to avoid timeouts
"""

from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from aws_lambda_powertools.utilities.typing import LambdaContext

from app.core.config import get_logger
from app.services.app import get_app
from app.slack.slack_events import process_pull_request_slack_event

logger = get_logger()


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Main Lambda entry point - routes between Slack webhook and pull request processing

    Flow:
    1. Slack sends webhook -> API Gateway -> Lambda (sync, 3s timeout)
    2. Slack handlers have an ack function which acknowledges immediately and triggers lazy async self-invocation
    3. Lazy Async invocation processes Bedrock query and responds to Slack

    If message starts with pr: then pull request id is extracted from message and it invokes lambda in pull request
    This message has a pull_request_processing property so when it is received by the lambda in the pull request
    It triggers function process_pull_request_slack_event
    """
    app = get_app(logger=logger)
    # handle pull request processing requests
    if event.get("pull_request_processing"):
        slack_event_data = event.get("slack_event")
        if not slack_event_data:
            logger.error("Pull request processing requested but no slack_event provided")
            return {"statusCode": 400}

        process_pull_request_slack_event(slack_event_data=slack_event_data)
        return {"statusCode": 200}

    # handle Slack webhook requests
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event=event, context=context)
