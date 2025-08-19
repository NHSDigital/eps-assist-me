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
from typing import Optional, Dict, Any

# Initialize Powertools Logger
logger = Logger(service="slackBotFunction")

# Initialize DynamoDB client - unified table for both dedup and conversations
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["SLACK_table"])

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
    """Check if event has already been processed using the unified table"""
    try:
        ttl = int(time.time()) + 3600  # 1 hour TTL
        table.put_item(
            Item={
                "pk": f"event#{event_id}",  # Use pk/sk pattern
                "sk": "dedup",
                "ttl": ttl,
                "timestamp": int(time.time()),
            },
            ConditionExpression="attribute_not_exists(pk)",  # Check pk instead of eventId
        )
        return False  # Item didn't exist, so not a duplicate
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return True  # Item already exists, so it's a duplicate
        return False


def get_conversation_session_id(conversation_key: str) -> Optional[str]:
    """Get existing Bedrock session ID for a conversation"""
    try:
        response = table.get_item(Key={"pk": conversation_key, "sk": "session"})
        if "Item" in response:
            logger.info(f"Found existing session: {response['Item']['session_id']}")
            return response["Item"]["session_id"]
        logger.info("No existing session found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving session: {e}")
        return None


def store_conversation_session_id(
    conversation_key: str, session_id: str, user_id: str, channel_id: str, thread_ts: Optional[str] = None
) -> None:
    """Store Bedrock session ID for a conversation"""
    try:
        ttl = int(time.time()) + 2592000  # 30 days
        table.put_item(
            Item={
                "pk": conversation_key,
                "sk": "session",
                "session_id": session_id,
                "user_id": user_id,
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "created_at": int(time.time()),
                "ttl": ttl,
            }
        )
        logger.info(f"Stored session {session_id} for conversation {conversation_key}")
    except Exception as e:
        logger.error(f"Error storing session: {e}")


def get_bedrock_knowledgebase_response(user_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Get Bedrock response with optional conversation context"""
    client = boto3.client(
        service_name="bedrock-agent-runtime",
        region_name=AWS_REGION,
    )

    request_params = {
        "input": {"text": user_query},
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": KNOWLEDGEBASE_ID,
                "modelArn": RAG_MODEL_ID,
                "generationConfiguration": {
                    "guardrailConfiguration": {
                        "guardrailId": GUARD_RAIL_ID,
                        "guardrailVersion": GUARD_VERSION,
                    }
                },
            },
        },
    }

    # Add session ID if provided (for conversation continuity)
    if session_id:
        request_params["sessionId"] = session_id
        logger.info(f"Using existing session ID: {session_id}")
    else:
        logger.info("Starting new conversation session")

    response = client.retrieve_and_generate(**request_params)
    logger.info(
        "Bedrock Knowledge Base Response received",
        extra={
            "response_session_id": response.get("sessionId"),
            "has_citations": len(response.get("citations", [])) > 0,
        },
    )
    return response


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


def process_async_slack_event(slack_event_data):
    """Process Slack event asynchronously with conversation memory"""
    event = slack_event_data["event"]
    event_id = slack_event_data["event_id"]
    token = slack_event_data["bot_token"]

    client = WebClient(token=token)

    try:
        raw_text = event["text"]
        user_id = event["user"]
        channel = event["channel"]
        thread_ts = event.get("thread_ts", event["ts"])

        # Determine conversation context
        if event.get("channel_type") == "im":
            # DM: continuous conversation per user
            conversation_key = f"dm#{channel}"
            context_type = "DM"
        else:
            # Channel @mention: thread-based conversation
            conversation_key = f"thread#{channel}#{thread_ts}"
            context_type = "thread"

        user_query = re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", raw_text).strip()

        logger.info(
            f"Processing async {context_type} message from user {user_id}",
            extra={"user_query": user_query, "conversation_key": conversation_key, "event_id": event_id},
        )

        if not user_query:
            client.chat_postMessage(
                channel=channel,
                text="Hi there! Please ask me a question and I'll help you find information from our knowledge base.",
                thread_ts=thread_ts,
            )
            return

        # Get existing session for conversation continuity
        session_id = get_conversation_session_id(conversation_key)

        # Query Bedrock with conversation context
        kb_response = get_bedrock_knowledgebase_response(user_query, session_id)
        response_text = kb_response["output"]["text"]

        # Store new session if this started a conversation
        if not session_id and "sessionId" in kb_response:
            store_conversation_session_id(
                conversation_key,
                kb_response["sessionId"],
                user_id,
                channel,
                thread_ts if context_type == "thread" else None,
            )
            context_indicator = f" (new {context_type} conversation)"
        elif session_id:
            context_indicator = f" (continuing {context_type} conversation)"
        else:
            context_indicator = ""

        client.chat_postMessage(channel=channel, text=f"{response_text}{context_indicator}", thread_ts=thread_ts)

    except Exception as err:
        logger.error(f"Error processing async message: {err}", extra={"event_id": event_id})
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
