"""
Core configuration for the Slack bot.
Sets up all the AWS and Slack connections we need.
"""

import os
import json
import boto3
from slack_bolt import App
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parameters import get_parameter

# set up logging
logger = Logger(service="slackBotFunction")

# DynamoDB table for deduplication and session storage
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["SLACK_BOT_STATE_TABLE"])

# get Slack credentials from Parameter Store
bot_token_parameter = os.environ["SLACK_BOT_TOKEN_PARAMETER"]
signing_secret_parameter = os.environ["SLACK_SIGNING_SECRET_PARAMETER"]

try:
    bot_token_raw = get_parameter(bot_token_parameter, decrypt=True)
    signing_secret_raw = get_parameter(signing_secret_parameter, decrypt=True)

    if not bot_token_raw or not signing_secret_raw:
        raise ValueError("Missing required parameters from Parameter Store")

    bot_token_data = json.loads(bot_token_raw)
    signing_secret_data = json.loads(signing_secret_raw)

    bot_token = bot_token_data.get("token")
    signing_secret = signing_secret_data.get("secret")

    if not bot_token or not signing_secret:
        raise ValueError("Missing required parameters: token or secret in Parameter Store values")

except json.JSONDecodeError as e:
    raise ValueError(f"Invalid JSON in Parameter Store: {e}")
except Exception as e:
    logger.error("Configuration error", extra={"error": str(e)})
    raise

# initialise the Slack app
app = App(
    process_before_response=True,
    token=bot_token,
    signing_secret=signing_secret,
)

# Bedrock configuration from environment
KNOWLEDGEBASE_ID = os.environ["KNOWLEDGEBASE_ID"]
RAG_MODEL_ID = os.environ["RAG_MODEL_ID"]
AWS_REGION = os.environ["AWS_REGION"]
GUARD_RAIL_ID = os.environ["GUARD_RAIL_ID"]
GUARD_VERSION = os.environ["GUARD_RAIL_VERSION"]

logger.info("Guardrail configuration loaded", extra={"guardrail_id": GUARD_RAIL_ID, "guardrail_version": GUARD_VERSION})

# Constants
FEEDBACK_PREFIX = "feedback:"
CONTEXT_TYPE_DM = "DM"
CONTEXT_TYPE_THREAD = "thread"
CHANNEL_TYPE_IM = "im"
SESSION_SK = "session"
DEDUP_SK = "dedup"
EVENT_PREFIX = "event#"
FEEDBACK_PREFIX_KEY = "feedback#"
USER_PREFIX = "user#"
DM_PREFIX = "dm#"
THREAD_PREFIX = "thread#"
NOTE_SUFFIX = "#note#"

# TTL constants (in seconds)
TTL_EVENT_DEDUP = 3600  # 1 hour
TTL_FEEDBACK = 7776000  # 90 days
TTL_SESSION = 2592000  # 30 days

# Bot response messages
BOT_MESSAGES = {
    "empty_query": "Hi there! Please ask me a question and I'll help you find information from our knowledge base.",
    "error_response": "Sorry, an error occurred while processing your request. Please try again later.",
    "feedback_positive_thanks": "Thank you for your feedback.",
    "feedback_negative_thanks": (
        'Please let us know how the answer could be improved. Start your message with "feedback:"'
    ),
    "feedback_thanks": "Thank you for your feedback.",
    "feedback_prompt": "Was this helpful?",
    "feedback_yes": "Yes",
    "feedback_no": "No",
}
