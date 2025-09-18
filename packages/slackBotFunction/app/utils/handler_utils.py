"""
Slack event handlers - handles @mentions and direct messages to the bot
"""

import time
import json
import traceback
from typing import Any, Dict
import boto3
from botocore.exceptions import ClientError
from slack_sdk import WebClient
from app.core.config import get_logger
import os
from mypy_boto3_cloudformation.client import CloudFormationClient
from mypy_boto3_lambda.client import LambdaClient

from app.services.dynamo import store_state_information

logger = get_logger()


def is_duplicate_event(event_id):
    """
    Check if we've already processed this event using DynamoDB conditional writes

    Slack may send duplicate events due to retries, so we use DynamoDB's
    conditional write to atomically check and record event processing.
    """
    try:
        ttl = int(time.time()) + 3600  # 1 hour TTL
        store_state_information(
            {"pk": f"event#{event_id}", "sk": "dedup", "ttl": ttl, "timestamp": int(time.time())},
            "attribute_not_exists(pk)",
        )
        return False  # Not a duplicate
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return True  # Duplicate
        logger.error("Error checking event duplication", extra={"error": traceback.format_exc()})
        return False


def trigger_async_processing(event_data):
    """
    Trigger asynchronous Lambda invocation to process Slack events

    Slack requires responses within 3 seconds, but Bedrock queries can take longer.
    This function invokes the same Lambda function asynchronously to handle the
    actual AI processing without blocking the initial Slack response.
    """
    # incase we fail to re-invoke the lambda we should log an error
    try:
        lambda_client: LambdaClient = boto3.client("lambda")
        lambda_client.invoke(
            FunctionName=os.environ["AWS_LAMBDA_FUNCTION_NAME"],
            InvocationType="Event",
            Payload=json.dumps({"async_processing": True, "slack_event": event_data}),
        )
        logger.info("Async processing triggered successfully")
    except Exception:
        logger.error("Failed to trigger async processing", extra={"error": traceback.format_exc()})


def respond_with_eyes(bot_token: str, event: Dict[str, Any]):
    client = WebClient(token=bot_token)
    channel = event["channel"]
    ts = event["ts"]
    try:
        logger.debug("Responding with eyes")
        client.reactions_add(channel=channel, timestamp=ts, name="eyes")
    except Exception:
        logger.warning("Failed to respond with eyes", extra={"error": traceback.format_exc()})


def trigger_pull_request_processing(pull_request_id: str, body: Dict[str, Any]):
    cloudformation_client: CloudFormationClient = boto3.client("cloudformation")
    lambda_client: LambdaClient = boto3.client("lambda")
    try:
        logger.debug("Getting arn for pull request", extra={"pull_request_id": pull_request_id})
        response = cloudformation_client.describe_stacks(StackName=f"epsam-pr-{pull_request_id}")
        outputs = {o["OutputKey"]: o["OutputValue"] for o in response["Stacks"][0]["Outputs"]}

        pull_request_lambda_arn = outputs.get("SlackBotLambdaArn")
        logger.debug("Triggering pull request lambda", extra={"lambda_arn": pull_request_lambda_arn})
        lambda_payload = {"body": json.dumps(body)}
        response = lambda_client.invoke(
            FunctionName=pull_request_lambda_arn, InvocationType="Event", Payload=json.dumps(lambda_payload)
        )
        logger.info("Triggered pull request lambda", extra={"lambda_arn": pull_request_lambda_arn})
    except Exception as e:
        logger.error("Failed to trigger pull request lambda", extra={"error": traceback.format_exc()})
        raise e
