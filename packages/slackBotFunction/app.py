import os
import json
import boto3
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parameters import get_parameter
from aws_lambda_powertools.utilities.typing import LambdaContext

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
    Note: This uses the global AWS Lambda Powertools logger instead of the default Slack Bolt logger
    to maintain consistent logging across the application.
    """
    logger.debug("Slack request received", extra={"body": body})
    return next()


def respond_to_mention_within_3_seconds(event, say):
    """
    Slack Bot @mention requires an Ack response within 3 seconds or it
    messages an operation timeout error to the user in the chat thread.

    The SlackBolt library provides a Async Ack function then re-invokes this Lambda
    to LazyLoad the process_mention_request that calls the Bedrock KB RetrieveAndGenerate API.

    This function is called initially to acknowledge the @mention within 3 secs.
    """
    try:
        user_query = event["text"]
        user_id = event["user"]
        thread_ts = event.get("thread_ts", event["ts"])

        logger.info(
            f"Acknowledging @mention from user {user_id}",
            extra={"user_query": user_query, "thread_ts": thread_ts},
        )

    except Exception as err:
        logger.error(f"Error acknowledging @mention: {err}")
        thread_ts = event.get("thread_ts", event["ts"])
        say(text="Sorry, an error occurred. Please try again later.", thread_ts=thread_ts)


def process_mention_request(event, say):
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
            extra={"user_query": user_query, "thread_ts": thread_ts},
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
        logger.error(f"Error processing @mention: {err}")
        thread_ts = event.get("thread_ts", event["ts"])
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
def handle_app_mention(event, say):
    """Handle when the bot is @mentioned"""
    respond_to_mention_within_3_seconds(event, say)
    # Process the actual request asynchronously
    process_mention_request(event, say)


# Handle direct messages
@app.event("message")
def handle_direct_message(event, say):
    """Handle direct messages to the bot"""
    # Only respond to direct messages (not channel messages)
    if event.get("channel_type") == "im":
        respond_to_mention_within_3_seconds(event, say)
        process_mention_request(event, say)


# Lambda handler method.
@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Lambda invoked for Slack bot", extra={"event": event})
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
