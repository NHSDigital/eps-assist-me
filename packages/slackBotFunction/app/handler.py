from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from app.slack.slack_handlers import get_app
from app.slack.slack_events import process_async_slack_event

logger = Logger(service="slackBotFunction")


@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Lambda invoked for Slack bot", extra={"event": event})

    if event.get("async_processing"):
        process_async_slack_event(event["slack_event"])
        return {"statusCode": 200}

    slack_handler = SlackRequestHandler(app=get_app())
    return slack_handler.handle(event, context)
