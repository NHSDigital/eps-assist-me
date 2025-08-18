import os
import re
import json
import boto3
import time
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_sdk import WebClient
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parameters import get_parameter
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from query_reformulator import reformulate_query


# Initialize Powertools Logger
logger = Logger(service="slackBotFunction")

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["SLACK_BOT_STATE_TABLE"])

# Get parameter names from environment variables
bot_token_parameter = os.environ["SLACK_BOT_TOKEN_PARAMETER"]
signing_secret_parameter = os.environ["SLACK_SIGNING_SECRET_PARAMETER"]

# Retrieve and parse parameters from SSM Parameter Store
bot_token_raw = get_parameter(bot_token_parameter, decrypt=True)
signing_secret_raw = get_parameter(signing_secret_parameter, decrypt=True)

# Parse JSON values and extract tokens
bot_token = json.loads(bot_token_raw)["token"]
signing_secret = json.loads(signing_secret_raw)["secret"]

# Initialize Slack app
app = App(
    process_before_response=True,
    token=bot_token,
    signing_secret=signing_secret,
)

# Get the expected AWS account params to local vars.
KNOWLEDGEBASE_ID = os.environ["KNOWLEDGEBASE_ID"]
RAG_MODEL_ID = os.environ["RAG_MODEL_ID"]
AWS_REGION = os.environ["AWS_REGION"]
GUARD_RAIL_ID = os.environ["GUARD_RAIL_ID"]
GUARD_VERSION = os.environ["GUARD_RAIL_VERSION"]

logger.info(f"Guardrail ID: {GUARD_RAIL_ID}, Version: {GUARD_VERSION}")


@app.middleware
def log_request(slack_logger, body, next):
    """
    Middleware to log incoming Slack requests using AWS Lambda Powertools logger.
    """
    logger.debug("Slack request received", extra={"body": body})
    return next()


def is_duplicate_event(event_id):
    """Check if event has already been processed using conditional put"""
    try:
        ttl = int(time.time()) + 3600  # 1 hour TTL
        table.put_item(
            Item={"eventId": event_id, "ttl": ttl, "timestamp": int(time.time())},
            ConditionExpression="attribute_not_exists(eventId)",
        )
        return False  # Item didn't exist, so not a duplicate
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return True  # Item already exists, so it's a duplicate
        return False


def trigger_async_processing(event_data):
    """
    Trigger async processing of the Slack event to avoid timeout issues.
    """
    lambda_client = boto3.client("lambda")
    lambda_client.invoke(
        FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"],
        InvocationType="Event",
        Payload=json.dumps({"async_processing": True, "slack_event": event_data}),
    )


def get_bedrock_knowledgebase_response(user_query):
    """
    Get and return the Bedrock Knowledge Base RetrieveAndGenerate response.
    """
    client = boto3.client(
        service_name="bedrock-agent-runtime",
        region_name=AWS_REGION,
    )

    query_input = {
        "text": user_query,
    }

    config = {
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            "generationConfiguration": {
                "guardrailConfiguration": {
                    "guardrailId": GUARD_RAIL_ID,
                    "guardrailVersion": GUARD_VERSION,
                },
            },
            "knowledgeBaseId": KNOWLEDGEBASE_ID,
            "modelArn": RAG_MODEL_ID,
        },
    }

    response = client.retrieve_and_generate(input=query_input, retrieveAndGenerateConfiguration=config)
    logger.info("Bedrock Knowledge Base Response received", extra={"response": response})
    return response


def process_async_slack_event(slack_event_data):
    """Process Slack event asynchronously"""
    event = slack_event_data["event"]
    event_id = slack_event_data["event_id"]
    token = slack_event_data["bot_token"]

    client = WebClient(token=token)

    try:
        raw_text = event["text"]
        user_id = event["user"]
        channel = event["channel"]
        thread_ts = event.get("thread_ts", event["ts"])

        user_query = re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", raw_text).strip()

        logger.info(
            f"Processing async @mention from user {user_id}",
            extra={"user_query": user_query, "thread_ts": thread_ts, "event_id": event_id},
        )

        if not user_query:
            client.chat_postMessage(
                channel=channel,
                text="Hi there! Please ask me a question and I'll help you find information from our knowledge base.",
                thread_ts=thread_ts,
            )
            return

        # Reformulate query for better RAG retrieval
        reformulated_query = reformulate_query(user_query)
        kb_response = get_bedrock_knowledgebase_response(reformulated_query)
        response_text = kb_response["output"]["text"]

        client.chat_postMessage(channel=channel, text=response_text, thread_ts=thread_ts)

    except Exception as err:
        logger.error(f"Error processing async @mention: {err}", extra={"event_id": event_id})
        client.chat_postMessage(
            channel=channel,
            text="Sorry, an error occurred while processing your request. Please try again later.",
            thread_ts=thread_ts,
        )


# Handle @mentions in channels and DMs
@app.event("app_mention")
def handle_app_mention(event, ack, body):
    """Handle when the bot is @mentioned"""
    ack()

    event_id = body.get("event_id")
    if not event_id:
        logger.warning("Missing event_id in Slack event body.")
    elif is_duplicate_event(event_id):
        logger.info(f"Duplicate event detected, skipping: {event_id}")
        return

    user_id = event.get("user", "unknown")
    logger.info(f"Processing @mention from user {user_id}", extra={"event_id": event_id})

    trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})


# Handle direct messages
@app.event("message")
def handle_direct_message(event, ack, body):
    """Handle direct messages to the bot"""
    ack()

    if event.get("channel_type") == "im":
        event_id = body.get("event_id")
        if not event_id:
            logger.warning("Missing event_id in Slack event body.")
        elif is_duplicate_event(event_id):
            logger.info(f"Duplicate event detected, skipping: {event_id}")
            return

        user_id = event.get("user", "unknown")
        logger.info(f"Processing DM from user {user_id}", extra={"event_id": event_id})

        trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})


@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Lambda invoked for Slack bot", extra={"event": event})

    if event.get("async_processing"):
        process_async_slack_event(event["slack_event"])
        return {"statusCode": 200}

    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
