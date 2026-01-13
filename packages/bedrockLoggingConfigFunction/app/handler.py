"""
cloudformation has no native resource for bedrock model invocation logging
this custom resource bridges that gap via the bedrock api
"""

import json
import os
import traceback
import boto3
import urllib3
from aws_lambda_powertools import Logger

http = urllib3.PoolManager()
logger = Logger()


def send_response(event, context, response_status, response_data, physical_resource_id=None, reason=None):
    """
    signals cloudformation that the custom resource operation completed
    """
    response_url = event["ResponseURL"]

    response_body = {
        "Status": response_status,
        "Reason": reason or f"See CloudWatch Log Stream: {context.log_stream_name}",
        "PhysicalResourceId": physical_resource_id or context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "Data": response_data,
    }

    json_response_body = json.dumps(response_body)

    headers = {"content-type": "", "content-length": str(len(json_response_body))}

    try:
        http.request("PUT", response_url, body=json_response_body, headers=headers)
        logger.info(f"cloudformation response sent: {response_status}")
    except Exception as e:
        logger.error(f"failed to signal cloudformation: {str(e)}")


def parse_event(event):
    """parse event to determine request type, properties, and logging state"""
    is_direct_invocation = not event or "RequestType" not in event

    if is_direct_invocation:
        logger.info("direct invocation detected - treating as Update operation")
        request_type = "Update"
        resource_properties = event if event else {}

        # check for enable_logging override in event, otherwise use env var
        if "enable_logging" in event:
            enable_logging = str(event.get("enable_logging", "true")).lower() == "true"
            logger.info(f"using enable_logging from event payload: {enable_logging}")
        else:
            enable_logging = os.environ.get("ENABLE_LOGGING", "true").lower() == "true"
            logger.info(f"using ENABLE_LOGGING from environment: {enable_logging}")
    else:
        # cloudformation invocation - always use env var
        request_type = event["RequestType"]
        resource_properties = event.get("ResourceProperties", {})
        enable_logging = os.environ.get("ENABLE_LOGGING", "true").lower() == "true"
        logger.info(f"cloudformation invocation - using ENABLE_LOGGING from environment: {enable_logging}")

    return request_type, resource_properties, enable_logging, is_direct_invocation


def handle_logging_disabled(event, context, bedrock, is_direct_invocation):
    """handle case when logging is disabled"""
    logger.info("bedrock logging disabled - removing configuration")
    try:
        bedrock.delete_model_invocation_logging_configuration()
        logger.info("bedrock logging configuration deleted")
    except bedrock.exceptions.ResourceNotFoundException:
        logger.info("logging configuration not found (already disabled)")

    # only send cloudformation response if this is a real cfn event
    if not is_direct_invocation:
        send_response(
            event,
            context,
            "SUCCESS",
            {"Message": "Bedrock logging disabled via environment variable"},
            physical_resource_id="BedrockModelInvocationLogging",
        )


def handle_create_or_update(event, context, bedrock, is_direct_invocation):
    """handle create or update operations"""
    logger.info("configuring bedrock model invocation logging")

    # Get CloudWatch config from environment variables (set by CDK)
    cloudwatch_log_group_name = os.environ.get("CLOUDWATCH_LOG_GROUP_NAME")
    cloudwatch_role_arn = os.environ.get("CLOUDWATCH_ROLE_ARN")

    # aws requires at least one logging destination
    if not cloudwatch_log_group_name or not cloudwatch_role_arn:
        error_msg = """
        CLOUDWATCH_LOG_GROUP_NAME and CLOUDWATCH_ROLE_ARN environment variables required.
        Cannot configure logging without destination."""

        logger.error(error_msg)
        if is_direct_invocation:
            raise ValueError(error_msg)
        send_response(event, context, "FAILED", {}, reason=error_msg)
        return

    logging_config = {
        "cloudWatchConfig": {
            "logGroupName": cloudwatch_log_group_name,
            "roleArn": cloudwatch_role_arn,
        },
    }

    logger.info(f"cloudwatch logs enabled: {cloudwatch_log_group_name}")

    response = bedrock.put_model_invocation_logging_configuration(loggingConfig=logging_config)
    logger.info(f"bedrock logging configured: {json.dumps(response)}")

    # only send cloudformation response if this is a real cfn event
    if not is_direct_invocation:
        send_response(
            event,
            context,
            "SUCCESS",
            {
                "Message": "Bedrock model invocation logging configured successfully",
                "CloudWatchLogGroup": cloudwatch_log_group_name,
            },
            physical_resource_id="BedrockModelInvocationLogging",
        )


def handle_delete(event, context, bedrock, is_direct_invocation):
    """handle delete operations"""
    logger.info("deleting bedrock model invocation logging")

    try:
        bedrock.delete_model_invocation_logging_configuration()
        logger.info("bedrock logging configuration deleted")
    except bedrock.exceptions.ResourceNotFoundException:
        logger.info("logging configuration not found")

    # only send cloudformation response if this is a real cfn event
    if not is_direct_invocation:
        send_response(
            event,
            context,
            "SUCCESS",
            {"Message": "Bedrock model invocation logging deleted successfully"},
            physical_resource_id="BedrockModelInvocationLogging",
        )


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event, context):
    """
    configures bedrock model invocation logging via put/delete api calls
    toggleable via ENABLE_LOGGING environment variable

    supports direct invocation in aws console with:
    - {} (empty) - uses ENABLE_LOGGING env var
    - {"enable_logging": true/false} - overrides env var
    """
    request_type, enable_logging, is_direct_invocation = parse_event(event)

    bedrock = boto3.client("bedrock")

    try:
        if request_type in ["Create", "Update"]:
            if not enable_logging:
                handle_logging_disabled(event, context, bedrock, is_direct_invocation)
                return
            handle_create_or_update(event, context, bedrock, is_direct_invocation)
        elif request_type == "Delete":
            handle_delete(event, context, bedrock, is_direct_invocation)
        else:
            if not is_direct_invocation:
                send_response(event, context, "FAILED", {}, reason=f"unsupported request type: {request_type}")
    except Exception as e:
        error_message = f"error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_message)
        if not is_direct_invocation:
            send_response(event, context, "FAILED", {}, reason=error_message)
        else:
            raise  # re-raise for direct invocations so user sees the error
