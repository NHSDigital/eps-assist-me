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

# Get the expected slack and AWS account params to local vars.
SLACK_SLASH_COMMAND = os.environ["SLACK_SLASH_COMMAND"]
KNOWLEDGEBASE_ID = os.environ["KNOWLEDGEBASE_ID"]
RAG_MODEL_ID = os.environ["RAG_MODEL_ID"]
AWS_REGION = os.environ["AWS_REGION"]
GUARD_RAIL_ID = os.environ["GUARD_RAIL_ID"]
GUARD_VERSION = os.environ["GUARD_RAIL_VERSION"]

logger.info(f"Guardrail ID: {GUARD_RAIL_ID}, Version: {GUARD_VERSION}")


@app.middleware
def log_request(logger, body, next):  # Use SlackBolt logger
    """
    SlackBolt library logging.
    """
    logger.debug(body)
    return next()


def respond_to_slack_within_3_seconds(body, ack):
    """
    Slack Bot Slash Command requires an Ack response within 3 seconds or it
    messages an operation timeout error to the user in the chat thread.

    The SlackBolt library provides a Async Ack function then re-invokes this Lambda
    to LazyLoad the process_command_request command that calls the Bedrock KB ReteriveandGenerate API.

    This function is called initially to acknowledge the Slack Slash command within 3 secs.
    """
    try:
        user_query = body["text"]
        logger.info(
            f"Acknowledging command: {SLACK_SLASH_COMMAND}",
            extra={"user_query": user_query},
        )
        ack(f"\n{SLACK_SLASH_COMMAND} - Processing Request: {user_query}")

    except Exception as err:
        logger.error(f"Error acknowledging command: {err}")
        ack(f"{SLACK_SLASH_COMMAND} - Sorry an error occurred. Please try again later.")


def process_command_request(respond, body):
    """
    Receive the Slack Slash Command user query and proxy the query to Bedrock Knowledge base ReteriveandGenerate API
    and return the response to Slack to be presented in the users chat thread.
    """
    try:
        user_query = body["text"]
        logger.info(
            f"Processing command: {SLACK_SLASH_COMMAND}",
            extra={"user_query": user_query},
        )

        kb_response = get_bedrock_knowledgebase_response(user_query)
        response_text = kb_response["output"]["text"]
        respond(f"\n{SLACK_SLASH_COMMAND} - Response: {response_text}\n")

    except Exception as err:
        logger.error(f"Error processing command: {err}")
        respond(f"{SLACK_SLASH_COMMAND} - Sorry an error occurred. Please try again later.")


def get_bedrock_knowledgebase_response(user_query):
    """
    Get and return the Bedrock Knowledge Base ReteriveAndGenerate response.
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


# Init the Slack Slash '/' command handler.
app.command(SLACK_SLASH_COMMAND)(
    ack=respond_to_slack_within_3_seconds,
    lazy=[process_command_request],
)

# Init the Slack Bolt logger and log handlers.
SlackRequestHandler.clear_all_log_handlers()


# Lambda handler method.
@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict:
    logger.info(f"Lambda invoked for {SLACK_SLASH_COMMAND}", extra={"event": event})
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
