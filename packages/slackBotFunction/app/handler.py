"""
Main Lambda handler - dual-purpose function for Slack bot operations

This Lambda function serves two purposes:
1. Handles incoming Slack events (webhooks) via API Gateway
2. Processes async operations when invoked by itself to avoid timeouts
"""

from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from aws_lambda_powertools.utilities.typing import LambdaContext

from typing import Any

from app.core.config import get_logger
from app.core.types import (
    DirectInvocationResponse,
    is_valid_direct_request,
    create_success_response,
    create_error_response,
)
from app.services.app import get_app
from app.slack.slack_events import process_pull_request_slack_action, process_pull_request_slack_event

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
    This message has a pull_request_event property so when it is received by the lambda in the pull request
    It triggers function process_pull_request_slack_event
    When a session is started with a pr: prefix, the pull request is stored in dynamo
    When subsequent actions or events are processed, this is looked up, and if it exists, then the pull request lambda
    is triggered with either pull_request_event or pull_request_action
    """
    # direct invocation bypasses slack infrastructure entirely
    if event.get("invocation_type") == "direct":
        return handle_direct_invocation(event, context)

    app = get_app(logger=logger)
    # handle pull request processing requests
    if event.get("pull_request_event"):
        slack_event_data = event.get("slack_event")
        if not slack_event_data:
            logger.error("Pull request processing requested but no slack_event provided")
            return {"statusCode": 400}

        process_pull_request_slack_event(slack_event_data=slack_event_data)
        return {"statusCode": 200}
    if event.get("pull_request_action"):
        slack_body_data = event.get("slack_body")
        if not slack_body_data:
            logger.error("Pull request processing requested but no slack_event provided")
            return {"statusCode": 400}

        process_pull_request_slack_action(slack_body_data=slack_body_data)
        return {"statusCode": 200}

    # handle Slack webhook requests
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event=event, context=context)


def handle_direct_invocation(event: dict[str, Any], context: LambdaContext) -> DirectInvocationResponse:
    """direct lambda invocation for ai assistance - bypasses slack entirely"""
    try:
        # validate request structure using type guard
        if not is_valid_direct_request(event):
            return create_error_response(400, "Missing required field: query")

        query = event["query"]
        session_id = event.get("session_id")

        # shared logic: same AI processing as slack handlers use
        from app.services.ai_processor import process_ai_query

        ai_response = process_ai_query(query, session_id)

        return create_success_response(
            text=ai_response["text"],
            session_id=ai_response["session_id"],
            citations=ai_response["citations"],
        )
    except Exception as e:
        logger.error(f"Error in direct invocation: {e}")
        return create_error_response(500, "Internal server error")
