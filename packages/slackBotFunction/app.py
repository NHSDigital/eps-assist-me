import os
import json
import boto3
import logging
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


# ================== Helper: AWS SSM Parameter Store ==================
def get_parameter(parameter_name):
    """
    Retrieve a parameter value from AWS SSM Parameter Store.
    If the value is a JSON string, return the first value.
    Returns raw string otherwise.
    Raises on any error.
    """
    ssm = boto3.client("ssm")
    try:
        response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        parameter_value = response["Parameter"]["Value"]

        try:
            # Attempt to parse value as JSON and return the first item.
            json_value = json.loads(parameter_value)
            value = next(iter(json_value.values()))
            return value
        except (json.JSONDecodeError, StopIteration):
            # Return as string if not valid JSON.
            return parameter_value

    except Exception as e:
        logging.error(f"Error getting parameter {parameter_name}: {str(e)}")
        raise


# ================== Load Sensitive Configuration ==================
# Retrieve Slack bot token and signing secret from environment/SSM.
bot_token_parameter = os.environ["SLACK_BOT_TOKEN_PARAMETER"]
signing_secret_parameter = os.environ["SLACK_SIGNING_SECRET_PARAMETER"]

bot_token = get_parameter(bot_token_parameter)
signing_secret = get_parameter(signing_secret_parameter)


# ================== Initialize Slack Bolt App ==================
# Set process_before_response=True to ensure middleware (like logging) runs before Slack gets a response.
app = App(
    process_before_response=True,
    token=bot_token,
    signing_secret=signing_secret,
)


# ================== Load Other Config from Environment ==================
SLACK_SLASH_COMMAND = os.environ["SLACK_SLASH_COMMAND"]
KNOWLEDGEBASE_ID = os.environ["KNOWLEDGEBASE_ID"]
RAG_MODEL_ID = os.environ["RAG_MODEL_ID"]
AWS_REGION = os.environ["AWS_REGION"]
GUARD_RAIL_ID = os.environ["GUARD_RAIL_ID"]
GUARD_VERSION = os.environ["GUARD_RAIL_VERSION"]

logging.info(f"GUARD_RAIL_ID: {GUARD_RAIL_ID}")
logging.info(f"GUARD_VERSION: {GUARD_VERSION}")


# ================== Middleware: Log All Incoming Slack Requests ==================
@app.middleware
def log_request(logger, body, next):
    """
    Log the entire incoming Slack event body for debugging/audit purposes.
    """
    logger.debug(body)
    return next()


# ================== Immediate Ack Handler for Slash Command ==================
def respond_to_slack_within_3_seconds(body, ack):
    """
    Immediately acknowledge the incoming slash command to Slack
    (must respond in <3 seconds or Slack will show a timeout error).
    Main processing happens asynchronously in the lazy handler.
    """
    try:
        user_query = body["text"]
        logging.info(
            f"Acknowledging slash command {SLACK_SLASH_COMMAND} - User Query: {user_query}"
        )
        ack(f"\nProcessing Request: {user_query}")
    except Exception as err:
        logging.error(f"Ack handler error: {err}")


# ================== Main Business Logic for Slash Command ==================
def process_command_request(respond, body):
    """
    Handle user slash command asynchronously (runs after immediate ack).
    - Calls Bedrock Knowledge Base with the user's question.
    - Posts answer as a reply in thread (if present) or as a standalone message.
    """
    try:
        user_query = body["text"]
        channel_id = body["channel_id"]
        user_id = body["user_id"]
        # Use thread_ts for thread replies, or fallback to message_ts
        thread_ts = body.get("thread_ts") or body.get("message_ts")

        logging.info(
            f"Processing command: {SLACK_SLASH_COMMAND} - User Query: {user_query}"
        )

        kb_response = get_bedrock_knowledgebase_response(user_query)
        response_text = kb_response["output"]["text"]

        client = WebClient(token=bot_token)

        # Prepare payload: reply in thread if thread_ts is provided.
        message_payload = {
            "channel": channel_id,
            "text": f"*Question from <@{user_id}>:*\n{user_query}\n\n*Answer:*\n{response_text}"
        }
        if thread_ts:
            message_payload["thread_ts"] = thread_ts

        client.chat_postMessage(**message_payload)

    except SlackApiError as e:
        logging.error(f"Slack API error posting message: {e.response['error']}")
    except Exception as err:
        logging.error(f"Handler error: {err}")


# ================== Bedrock Knowledge Base Interaction ==================
def get_bedrock_knowledgebase_response(user_query):
    """
    Query the AWS Bedrock Knowledge Base RetrieveAndGenerate API using the user's question.
    Loads all Bedrock client config inside the function (avoids Lambda cold start delays in ack handler).
    Requires the following global variables: AWS_REGION, GUARD_RAIL_ID, GUARD_VERSION, KNOWLEDGEBASE_ID, RAG_MODEL_ID.
    """
    client = boto3.client(
        service_name="bedrock-agent-runtime",
        region_name=AWS_REGION,
    )

    input = {
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

    response = client.retrieve_and_generate(
        input=input, retrieveAndGenerateConfiguration=config
    )
    logging.info(f"Bedrock Knowledge Base Response: {response}")
    return response


# ================== Slash Command Registration ==================
# Register the Slack slash command handler with Bolt:
# - ack handler responds immediately (must be <3s)
# - lazy handler processes the command asynchronously
app.command(SLACK_SLASH_COMMAND)(
    ack=respond_to_slack_within_3_seconds,
    lazy=[process_command_request],
)


# ================== Logging Setup ==================
# Remove default handlers and configure root logger for DEBUG output.
SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)


# ================== AWS Lambda Entrypoint ==================
def handler(event, context):
    """
    AWS Lambda entrypoint: Handles Slack requests via Slack Bolt's AWS adapter.
    This function is called by AWS Lambda when the function is invoked.
    """
    logging.info(f"{SLACK_SLASH_COMMAND} - Event: {event}")
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
