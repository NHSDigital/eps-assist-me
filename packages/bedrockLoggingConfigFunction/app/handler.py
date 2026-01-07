"""
cloudformation has no native resource for bedrock model invocation logging
this custom resource bridges that gap via the bedrock api
"""

import json
import traceback
import boto3
import urllib3

http = urllib3.PoolManager()


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
        print(f"cloudformation response sent: {response_status}")
    except Exception as e:
        print(f"failed to signal cloudformation: {str(e)}")


def handler(event, context):
    """
    configures bedrock model invocation logging via put/delete api calls
    """
    print(f"received event: {json.dumps(event)}")

    request_type = event["RequestType"]
    resource_properties = event.get("ResourceProperties", {})

    cloudwatch_log_group_name = resource_properties.get("CloudWatchLogGroupName")
    cloudwatch_role_arn = resource_properties.get("CloudWatchRoleArn")
    s3_bucket_name = resource_properties.get("S3BucketName", "")
    s3_key_prefix = resource_properties.get("S3KeyPrefix", "bedrock-logs/")
    text_data_delivery_enabled = resource_properties.get("TextDataDeliveryEnabled", "true").lower() == "true"
    image_data_delivery_enabled = resource_properties.get("ImageDataDeliveryEnabled", "true").lower() == "true"
    embedding_data_delivery_enabled = resource_properties.get("EmbeddingDataDeliveryEnabled", "true").lower() == "true"

    bedrock = boto3.client("bedrock")

    try:
        if request_type in ["Create", "Update"]:
            print("configuring bedrock model invocation logging")

            logging_config = {
                "textDataDeliveryEnabled": text_data_delivery_enabled,
                "imageDataDeliveryEnabled": image_data_delivery_enabled,
                "embeddingDataDeliveryEnabled": embedding_data_delivery_enabled,
            }

            if cloudwatch_log_group_name and cloudwatch_role_arn:
                logging_config["cloudWatchConfig"] = {
                    "logGroupName": cloudwatch_log_group_name,
                    "roleArn": cloudwatch_role_arn,
                }
                print(f"cloudwatch logs enabled: {cloudwatch_log_group_name}")

            if s3_bucket_name:
                logging_config["s3Config"] = {"bucketName": s3_bucket_name, "keyPrefix": s3_key_prefix}
                print(f"s3 logging enabled: s3://{s3_bucket_name}/{s3_key_prefix}")

            response = bedrock.put_model_invocation_logging_configuration(loggingConfig=logging_config)

            print(f"bedrock logging configured: {json.dumps(response)}")

            send_response(
                event,
                context,
                "SUCCESS",
                {
                    "Message": "Bedrock model invocation logging configured successfully",
                    "CloudWatchLogGroup": cloudwatch_log_group_name,
                    "S3Bucket": s3_bucket_name,
                },
                physical_resource_id="BedrockModelInvocationLogging",
            )

        elif request_type == "Delete":
            print("deleting bedrock model invocation logging")

            try:
                bedrock.delete_model_invocation_logging_configuration()
                print("bedrock logging configuration deleted")
            except bedrock.exceptions.ResourceNotFoundException:
                # already deleted or never existed
                print("logging configuration not found")

            send_response(
                event,
                context,
                "SUCCESS",
                {"Message": "Bedrock model invocation logging deleted successfully"},
                physical_resource_id="BedrockModelInvocationLogging",
            )

        else:
            send_response(event, context, "FAILED", {}, reason=f"unsupported request type: {request_type}")

    except Exception as e:
        error_message = f"error: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        send_response(event, context, "FAILED", {}, reason=error_message)
