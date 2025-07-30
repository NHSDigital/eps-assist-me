import os
import json
import boto3
import logging
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


# Get params from SSM
def get_parameter(parameter_name):
    ssm = boto3.client("ssm")
    try:
        response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        # Parse the JSON string from the parameter
        parameter_value = response["Parameter"]["Value"]

        # Remove the JSON structure and extract just the value
        try:
            json_value = json.loads(parameter_value)
            # Get the first value from the dictionary
            value = next(iter(json_value.values()))
            return value
        except (json.JSONDecodeError, StopIteration):
            # If parsing fails or dictionary is empty, return the raw value
            return parameter_value

    except Exception as e:
        logging.error(f"Error getting parameter {parameter_name}: {str(e)}")
        raise


# Get parameter names from environment variables
bot_token_parameter = os.environ["SLACK_BOT_TOKEN_PARAMETER"]
signing_secret_parameter = os.environ["SLACK_SIGNING_SECRET_PARAMETER"]

# Retrieve the parameters from SSM Parameter Store
bot_token = get_parameter(bot_token_parameter)
signing_secret = get_parameter(signing_secret_parameter)

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

print(f"GR_ID,{GUARD_RAIL_ID}")
print(f"GR_V, {GUARD_VERSION}")


@app.middleware
def log_request(logger, body, next):
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
        logging.info(
            f"Acknowledging slash command {SLACK_SLASH_COMMAND} - User Query: {user_query}"
        )
        ack(f"\nProcessing Request: {user_query}")
    except Exception as err:
        logging.error(f"Ack handler error: {err}")


def process_command_request(respond, body):
    """
    Receive the Slack Slash Command user query and proxy the query to Bedrock Knowledge base ReteriveandGenerate API
    and return the response to Slack to be presented in the users chat thread.
    """
    try:
        # Get the user query
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

    response = client.retrieve_and_generate(
        input=query_input, retrieveAndGenerateConfiguration=config
    )
    logging.info(f"Bedrock Knowledge Base Response: {response}")
    return response


# Init the Slack Slash '/' command handler.
app.command(SLACK_SLASH_COMMAND)(
    ack=respond_to_slack_within_3_seconds,
    lazy=[process_command_request],
)

# Init the Slack Bolt logger and log handlers.
SlackRequestHandler.clear_all_log_handlers()
logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)


# Lambda handler method.
def handler(event, context):
    logging.info(f"{SLACK_SLASH_COMMAND} - Event: {event}")
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
