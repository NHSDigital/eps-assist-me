import os
import json
import boto3
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parameters import get_parameter
from aws_lambda_powertools.utilities.typing import LambdaContext

# In-memory cache for processed events (Lambda container reuse)
processed_events = set()
MAX_PROCESSED_EVENTS = 1000  # Prevent memory growth

# Initialize Powertools Logger
logger = Logger(service="slackBotFunction")

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


def manage_processed_events_cache():
    """
    Manage the size of processed_events cache to prevent memory issues.
    """
    global processed_events
    if len(processed_events) > MAX_PROCESSED_EVENTS:
        # Keep only the most recent half to prevent memory growth
        processed_events = set(list(processed_events)[-MAX_PROCESSED_EVENTS // 2 :])
        logger.info(f"Cleaned processed_events cache, now has {len(processed_events)} items")


def process_mention_request(event, say, event_id):
    """
    Process the @mention user query and proxy the query to Bedrock Knowledge base RetrieveAndGenerate API
    and return the response to Slack to be presented in the thread.
    """
    try:
        # Extract the user's query, removing the bot mention
        raw_text = event["text"]
        user_id = event["user"]
        thread_ts = event.get("thread_ts", event["ts"])  # Use thread_ts if in thread, otherwise use message ts

        # Remove bot mention from the text to get clean query
        # Bot mentions come in format <@U1234567890> or <@U1234567890|botname>
        import re

        user_query = re.sub(r"<@[UW][A-Z0-9]+(\|[^>]+)?>", "", raw_text).strip()

        logger.info(
            f"Processing @mention from user {user_id}",
            extra={"user_query": user_query, "thread_ts": thread_ts, "event_id": event_id},
        )

        if not user_query:
            say(
                text="Hi there! Please ask me a question and I'll help you find information from our knowledge base.",
                thread_ts=thread_ts,
            )
            return

        kb_response = get_bedrock_knowledgebase_response(user_query)
        response_text = kb_response["output"]["text"]

        # Reply in thread with the response
        say(text=response_text, thread_ts=thread_ts)

    except Exception as err:
        logger.error(f"Error processing @mention: {err}", extra={"event_id": event_id})
        thread_ts = event.get("thread_ts", event.get("ts"))
        say(text="Sorry, an error occurred while processing your request. Please try again later.", thread_ts=thread_ts)


def get_bedrock_knowledgebase_response(user_query):
    """
    Get and return the Bedrock Knowledge Base RetrieveAndGenerate response.
    Do all init tasks here instead of globally as initial invocation of this lambda
    provides Slack required ack in 3 sec. It doesn't trigger any bedrock functions and is
    time sensitive.
    """
    # Initialise the bedrock-runtime client (in default / running region).
    client = boto3.client(
        service_name="bedrock-agent-runtime",
        region_name=AWS_REGION,
    )

    # Create the RetrieveAndGenerateCommand input with the user query.
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


# Handle @mentions in channels and DMs
@app.event("app_mention")
def handle_app_mention(event, say, ack, body):
    """Handle when the bot is @mentioned"""
    # Use the official event_id from Slack for deduplication
    event_id = body.get("event_id")

    # Check if we've already processed this event
    if event_id in processed_events:
        logger.info(f"Skipping duplicate event {event_id}")
        ack()
        return

    # Mark event as processed and manage cache size
    processed_events.add(event_id)
    manage_processed_events_cache()

    # Acknowledge immediately to prevent Slack retries
    ack()

    # Log the acknowledgment
    user_id = event.get("user", "unknown")
    logger.info(f"Acknowledged @mention from user {user_id}", extra={"event_id": event_id})

    # Process the actual request
    process_mention_request(event, say, event_id)


# Handle direct messages
@app.event("message")
def handle_direct_message(event, say, ack, body):
    """Handle direct messages to the bot"""
    # Only respond to direct messages (not channel messages)
    if event.get("channel_type") == "im":
        # Use the official event_id from Slack for deduplication
        event_id = body.get("event_id")

        # Check if we've already processed this event
        if event_id in processed_events:
            logger.info(f"Skipping duplicate DM event {event_id}")
            ack()
            return

        # Mark event as processed and manage cache size
        processed_events.add(event_id)
        manage_processed_events_cache()

        # Acknowledge immediately to prevent Slack retries
        ack()

        # Log the acknowledgment
        user_id = event.get("user", "unknown")
        logger.info(f"Acknowledged DM from user {user_id}", extra={"event_id": event_id})

        # Process the actual request
        process_mention_request(event, say, event_id)


# Lambda handler method.
@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Lambda invoked for Slack bot", extra={"event": event})
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
