"""
Configuration module - initializes AWS clients, Slack app, and environment variables
"""

import os
import json
import boto3
from slack_bolt import App
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parameters import get_parameter

logger = Logger(service="slackBotFunction")

# Environment variables
KNOWLEDGEBASE_ID = os.environ["KNOWLEDGEBASE_ID"]
RAG_MODEL_ID = os.environ["RAG_MODEL_ID"]
AWS_REGION = os.environ["AWS_REGION"]
GUARD_RAIL_ID = os.environ["GUARD_RAIL_ID"]
GUARD_VERSION = os.environ["GUARD_RAIL_VERSION"]
SLACK_BOT_STATE_TABLE = os.environ["SLACK_BOT_STATE_TABLE"]
AWS_LAMBDA_FUNCTION_NAME = os.environ["AWS_LAMBDA_FUNCTION_NAME"]

# Parameter names
bot_token_parameter = os.environ["SLACK_BOT_TOKEN_PARAMETER"]
signing_secret_parameter = os.environ["SLACK_SIGNING_SECRET_PARAMETER"]

# AWS clients
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(SLACK_BOT_STATE_TABLE)

# Retrieve Slack credentials
bot_token_raw = get_parameter(bot_token_parameter, decrypt=True)
signing_secret_raw = get_parameter(signing_secret_parameter, decrypt=True)

bot_token = json.loads(bot_token_raw)["token"]
signing_secret = json.loads(signing_secret_raw)["secret"]

# Initialize Slack app
app = App(
    process_before_response=True,
    token=bot_token,
    signing_secret=signing_secret,
)

logger.info(f"Guardrail ID: {GUARD_RAIL_ID}, Version: {GUARD_VERSION}")

# Bot response messages
BOT_MESSAGES = {
    "empty_query": "Hi there! Please ask me a question and I'll help you find information from our knowledge base.",
    "error_response": "Sorry, an error occurred while processing your request. Please try again later.",
}
