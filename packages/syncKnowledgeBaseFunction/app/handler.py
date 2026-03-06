"""
Lambda handler for automatic Bedrock Knowledge Base synchronization

Triggered by S3 events (PUT/POST/DELETE) to automatically ingest new or updated
documents into the Bedrock Knowledge Base. This ensures the AI assistant always
has access to the latest documentation for answering user queries.
"""

import time
import traceback
import uuid
import boto3
import json
from typing import Literal
from botocore.exceptions import ClientError
from app.config.config import (
    KNOWLEDGEBASE_ID,
    DATA_SOURCE_ID,
    SUPPORTED_FILE_TYPES,
    AWS_ACCOUNT_ID,
    get_bot_token,
    logger,
)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

s3_client = boto3.client("s3")
bedrock_agent = boto3.client("bedrock-agent")


def is_supported_file_type(file_key):
    """
    Check if file type is supported for Bedrock Knowledge Base ingestion
    """
    return any(file_key.lower().endswith(ext) for ext in SUPPORTED_FILE_TYPES)


def get_unprocessed_files(s3_records) -> tuple[list, str, str, bool]:
    unprocessed_files = []
    new_process_key = uuid.uuid4().hex
    process_key = new_process_key
    bucket_name = ""

    try:
        if s3_records is None:
            return unprocessed_files, process_key, bucket_name, True

        bucket_name = s3_records[0]["s3"]["bucket"]["name"]

        paginator = s3_client.get_paginator("list_objects_v2")
        page_iterator = paginator.paginate(Bucket=bucket_name)

        for i, page in enumerate(page_iterator):
            if "Contents" not in page:
                logger.info(f"Skipping page ({i}) with no contents")
                continue

            for obj in page["Contents"]:
                file_key = obj["Key"]

                logger.log("")
                tag_response = s3_client.get_object_tagging(
                    Bucket=bucket_name, Key=file_key, ExpectedBucketOwner=AWS_ACCOUNT_ID
                )

                tags = {tag["Key"]: tag["Value"] for tag in tag_response.get("TagSet", [])}
                logger.info(f"Found tags for {file_key}", extra={"tags": tags})
                if not tags.get("Process_Status"):
                    unprocessed_files.append(file_key)
                    process_key = tags.get("Process_key", process_key)
                    break

        # Return a list of records which are not being processed by this function
        unprocessed_files = list(
            {s3_record.get("s3", {}).get("object", {}).get("key") for s3_record in s3_records} ^ set(unprocessed_files)
        )

        logger.info(
            "Found Unprocessed Files",
            extra={"count": len(unprocessed_files), "unprocessed_files": json.dumps(unprocessed_files)},
        )
    except Exception as e:
        logger.info(f"Error finding last modified file: {str(e)}")

    return unprocessed_files, process_key, bucket_name, (process_key == new_process_key)


def set_unprocessed_files(s3_records, unprocessed_files, key, bucket):
    tags = [{"Key": "Process_Key", "Value": key}]
    logger.info("Update tags on unprocessed files", extra={"tags": json.dumps(tags)})
    for file in unprocessed_files:
        s3_client.put_object_tagging(
            Bucket=bucket, Key=file, ExpectedBucketOwner=AWS_ACCOUNT_ID, Tagging={"TagSet": tags}
        )

    tags.append({"Key": "Process_Status", "Value": "Complete"})
    logger.info("Update tags on processed files", extra={"tags": json.dumps(tags)})
    for record in s3_records:
        s3_client.put_object_tagging(
            Bucket=bucket,
            Key=record["s3"]["bucket"]["name"],
            ExpectedBucketOwner=AWS_ACCOUNT_ID,
            Tagging={"TagSet": tags},
        )


def process_s3_records(records) -> tuple[bool, str, list, list]:
    """
    Process a S3 records, a single record can not be synced - the whole drive will be synced
    Files will be filtered by the knowledge base.

    Validates S3 record structure, checks file type support, and triggers
    Bedrock Knowledge Base ingestion for supported documents.
    """

    created = []
    deleted = []
    # Validate if the sync should occur by checking if any files are valid
    for i, record in enumerate(records):
        # Extract S3 event details
        s3_info = record.get("s3", {})
        bucket_name = s3_info.get("bucket", {}).get("name")
        object_key = s3_info.get("object", {}).get("key")

        # Skip malformed S3 records
        if not bucket_name or not object_key:
            logger.warning(
                "Skipping invalid S3 record",
                extra={
                    "record_index": i + 1,
                    "has_bucket": bool(bucket_name),
                    "has_object_key": bool(object_key),
                },
            )
            continue

        # Skip unsupported file types to avoid unnecessary processing
        if not is_supported_file_type(object_key):
            logger.info(
                "Skipping unsupported file type",
                extra={
                    "file_key": object_key,
                    "supported_types": list(SUPPORTED_FILE_TYPES),
                    "record_index": i + 1,
                },
            )
            continue

        # Extract additional event metadata for logging
        event_name = record["eventName"]
        object_size = s3_info.get("object", {}).get("size", "unknown")

        # Determine event type for proper handling
        is_delete_event = event_name.startswith("ObjectRemoved")
        is_create_event = event_name.startswith("ObjectCreated")
        is_update_event = event_name.startswith("ObjectModified")

        logger.info(
            "Found valid S3 event for processing",
            extra={
                "event_name": event_name,
                "bucket": bucket_name,
                "key": object_key,
                "object_size_bytes": object_size,
                "record_index": i + 1,
            },
        )

        # Determine event type based on S3 event name
        if is_delete_event:
            deleted.append(object_key)
        elif is_create_event or is_update_event:
            created.append(object_key)

    # If we have at-least 1 valid file, start the sync process
    if not created and not deleted:
        return False, None, [], []

    # Start Bedrock ingestion job (processes ALL files in data source)
    # For delete events, this re-ingests remaining files and removes deleted ones from vector index
    ingestion_start_time = time.time()

    # Create descriptive message based on event type
    description = "Auto-sync:"
    if is_delete_event:
        description += f"\nFiles deleted ({len(deleted)})"
    if is_create_event:
        description += f"\nFiles added/updated ({len(created)})"

    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=KNOWLEDGEBASE_ID,
        dataSourceId=DATA_SOURCE_ID,
        description=description,
    )
    ingestion_request_time = time.time() - ingestion_start_time

    job_id = response["ingestionJob"]["ingestionJobId"]
    job_status = response["ingestionJob"]["status"]

    # REVERT job_id and job_status
    logger.info(
        "Successfully started ingestion job",
        extra={
            "job_id": job_id,
            "job_status": job_status,
            "knowledge_base_id": KNOWLEDGEBASE_ID,
            "trigger_file": object_key,
            "ingestion_request_duration_ms": round(ingestion_request_time * 1000, 2),
            "description": description,
        },
    )

    return True, job_id, created, deleted


def handle_client_error(e, start_time, slack_client, slack_messages):
    """
    Handle AWS ClientError exceptions with appropriate responses

    Distinguishes between expected ConflictExceptions (job already running)
    and other AWS service errors, providing appropriate HTTP responses.
    """
    error_code = e.response.get("Error", {}).get("Code", "Unknown")
    error_message = e.response.get("Error", {}).get("Message", str(e))

    # ConflictException is expected when ingestion job already running
    if error_code == "ConflictException":
        logger.warning(
            "Ingestion job already in progress - no action required",
            extra={
                "status_code": 409,
                "error_code": error_code,
                "error_message": error_message,
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "explanation": "Normal when multiple files uploaded quickly",
            },
        )

        update_slack_complete(
            slack_client=slack_client, messages=slack_messages, feedback="Update already in progress."
        )
        return {
            "statusCode": 409,
            "body": "Files uploaded successfully - processing by existing ingestion job (no action required)",
        }
    else:
        update_slack_error(slack_client=slack_client, messages=slack_messages)

        # Handle other AWS service errors
        logger.error(
            "AWS service error occurred",
            extra={
                "status_code": 500,
                "error_code": error_code,
                "error_message": error_message,
                "duration_ms": round((time.time() - start_time) * 1000, 2),
            },
        )
        return {
            "statusCode": 500,
            "body": f"AWS error: {error_code} - {error_message}",
        }


def get_bot_channels(client):
    """
    Fetches all public and private channels the bot is a member of.
    """
    channel_ids = []
    try:
        for result in client.conversations_list(types=["private_channel"], limit=1000):
            for channel in result["channels"]:
                channel_ids.append(channel["id"])
    except Exception as e:
        logger.error(f"Network error listing channels: {str(e)}")
        return []

    return channel_ids


def get_latest_message(client, channel_id: str, user_id: str):
    history = client.conversation_history(channel=channel_id, limit=20)
    newest = None

    if history is None:
        logger.info(
            "No Slack conversation history could be found", extra={"channel_id": channel_id, "user_id": user_id}
        )

    # History is returned newest to oldest
    for message in history.get("messages", []):
        if message.get("user") == user_id:
            logger.info("Found existing Slack Message", extra={"message": message})
            newest = {"ok": history.get("ok"), "channel": channel_id, "ts": newest.get("ts"), "message": message}
            break

    return newest


def post_message(slack_client, channel_id: str, blocks: list, text_fallback: str):
    """
    Posts the formatted message to a specific channel.
    """
    try:
        return slack_client.chat_postMessage(channel=channel_id, text=text_fallback, blocks=blocks)
    except SlackApiError as e:
        logger.error(
            f"Error posting to {channel_id}: {str(e)}", extra={"blocks": blocks, "text_fallback": text_fallback}
        )
        return None
    except Exception as e:
        logger.error(
            f"Error posting to {channel_id}: {str(e)}", extra={"blocks": blocks, "text_fallback": text_fallback}
        )
        return None


def initialise_slack_messages(event_count: int, is_new: bool):
    """
    Send Slack notification summarizing the synchronization status
    """
    default_response = (None, [])
    try:
        # Build blocks for Slack message
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": "I am currently syncing changes to my knowledge base.\n This may take a few minutes.",
                },
            },
            {
                "type": "plan",
                "plan_id": "plan_1",
                "title": "Fetching changes...",
                "tasks": [create_task(title="Fetching changes", details=[], outputs=[f"Found {event_count} event(s)"])],
            },
            {
                "type": "context",
                "elements": [{"type": "plain_text", "text": "Please wait up-to 10 minutes for changes to take effect"}],
            },
        ]

        # Create new client
        token = get_bot_token()
        slack_client = WebClient(token=token)
        response = slack_client.auth_test()
        user_id = response.get("user_id", "unknown")

        logger.info(f"Authenticated as bot user: {user_id}", extra={"response": response})

        # Get Channels where the Bot is a member
        logger.info("Find bot channels...")
        target_channels = get_bot_channels(slack_client)

        if not target_channels:
            logger.warning("SKIPPING - Bot is not in any channels. No messages sent.")
            return default_response

        # Broadcast Loop
        logger.info(f"Broadcasting to {len(target_channels)} channels...")

        responses = []
        for channel_id in target_channels:
            try:
                response = None
                if is_new:
                    logger.info("Searching for existing Slack Message")
                    response = get_latest_message(slack_client, channel_id, user_id)

                if response is None:
                    logger.info("Creating new Slack Message")
                    response = post_message(
                        slack_client=slack_client,
                        channel_id=channel_id,
                        blocks=blocks,
                        text_fallback="*My knowledge base has been updated!*",
                    )

                responses.append(response)
                if response["ok"] is not True:
                    logger.error("Error initialising Slack Message.", extra={"response": response})
            except Exception as e:
                logger.error(f"Failed to initialise slack message for channel: {channel_id}", extra={"exception": e})
                continue

        logger.info("Broadcast complete.", extra={"responses": len(responses)})
        return slack_client, responses

    except Exception as e:
        logger.error(f"Failed to initialise slack messages: {str(e)}")
        return default_response


def update_slack_message(slack_client, response, blocks):
    """
    Update the existing Slack message blocks with new information
    """
    channel_id = response["channel"]
    ts = response["ts"]

    if slack_client is None:
        logger.warning("No Slack client found, skipping update message")

    try:
        logger.info("Updating Slack channel")
        result = slack_client.chat_update(channel=channel_id, ts=ts, blocks=blocks)
        logger.error("Error updating Slack Message.", extra={"response": result})
    except SlackApiError as e:
        logger.error(f"Error updating message in {channel_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating message in {channel_id}: {str(e)}")


def update_slack_task(
    plan,
    task,
    title=None,
    status: Literal["in_progress", "completed"] = "in_progress",
    details=None,
    outputs=None,
):
    logger.info("Updating Slack task")
    if not task:
        return plan

    if title:
        plan["title"] = f"{title}..."
        task["title"] = title

    if status:
        task["status"] = status

    if details:
        task["details"] = {
            "type": "rich_text",
            "block_id": uuid.uuid4().hex,
            "elements": [
                *task.get("details", {}).get("elements", []),
                *[{"type": "rich_text_section", "elements": [{"type": "text", "text": detail}]} for detail in details],
            ],
        }

    if outputs:
        task["output"] = {
            "type": "rich_text",
            "block_id": uuid.uuid4().hex,
            "elements": [
                {"type": "rich_text_section", "elements": [{"type": "text", "text": output}]} for output in outputs
            ],
        }

    return plan


def create_task(
    title,
    plan=None,
    details=None,
    outputs=None,
    status: Literal["in_progress", "complete"] = "in_progress",
):
    """
    Helper function to create a task object for the plan block
    """
    task = {
        "task_id": uuid.uuid4().hex,
        "title": title,
        "status": status,
        "details": {
            "type": "rich_text",
            "block_id": uuid.uuid4().hex,
            "elements": [
                {"type": "rich_text_section", "elements": [{"type": "text", "text": detail}]}
                for detail in (details if details else [])
            ],
        },
        "output": {
            "type": "rich_text",
            "block_id": uuid.uuid4().hex,
            "elements": [
                {"type": "rich_text_section", "elements": [{"type": "text", "text": output}]}
                for output in (outputs if outputs else [])
            ],
        },
    }

    if plan:
        plan["title"] = title
        plan["status"] = status
        plan["tasks"] += [task]
    return task


def update_slack_files_message(slack_client, response, added, deleted, index, skip):
    try:
        if response is None:
            logger.info(f"Skipping empty response ({index + 1})")
            return

        # Update the event count in the plan block
        blocks = response["message"]
        blocks = response["message"]["blocks"]
        plan = next((block for block in blocks if block["type"] == "plan"), None)
        task = plan["tasks"][-1] if plan and "tasks" in plan and plan["tasks"] else None

        # Task params
        title = "Processing file changes"
        status = "completed"
        details = [f"{val} {label} file(s)" for val, label in [(added, "new"), (deleted, "removed")] if val > 0]
        outputs = [f"Total files processed: {added + deleted}" if not skip else "No file changes"]

        if task and task["title"] == title:
            plan = update_slack_task(plan=plan, task=task, status=status, title=title, details=details, outputs=outputs)
        else:
            create_task(plan=plan, title=title, details=details, outputs=outputs, status=status)

        update_slack_message(slack_client=slack_client, response=response, blocks=blocks)
    except Exception as e:
        logger.error(
            "Unexpected error occurred updating Slack message",
            extra={
                "status_code": 500,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "error": traceback.format_exc(),
                "e": e,
            },
        )


def update_slack_files(slack_client, created_files: list[str], deleted_files: list[str], messages: list):
    """
    Update the existing Slack message blocks with the count of processed files
    """
    if not messages:
        logger.warning("No slack messages to update")
        return

    if not created_files and not deleted_files:
        logger.warning("No processed files to update in Slack messages.")
        return

    logger.info(
        "Processing lack files Slack Notification",
        extra={"created_files": created_files, "deleted_files": deleted_files, "messages": messages},
    )
    added = len(created_files)
    deleted = len(deleted_files)
    skip = (added + deleted) == 0

    logger.info(f"Processed {added} added/updated and {deleted} deleted file(s).")

    for i, response in enumerate(messages):
        update_slack_files_message(
            slack_client=slack_client, response=response, added=added, deleted=deleted, index=i, skip=skip
        )


def update_slack_complete(slack_client, messages, feedback: None):
    """
    Mark Slack Plan as complete
    """
    if not messages:
        logger.warning("No existing Slack messages to update event count.")

    for response in messages:
        try:
            if response is None:
                continue

            # Update the event count in the plan block
            blocks = response["message"]["blocks"]
            plan = next((block for block in blocks if block["type"] == "plan"), None)

            plan["title"] = feedback if feedback else "Processing complete!"
            for i, task in enumerate(plan["tasks"]):
                task["status"] = "complete"

            update_slack_message(slack_client, response, blocks)
        except Exception as e:
            logger.error(
                "Unexpected error occurred completing Slack message",
                extra={
                    "status_code": 500,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "error": traceback.format_exc(),
                    "e": e,
                },
            )


def update_slack_error(slack_client, messages):
    """
    Mark Slack Plan as errored
    """
    if not messages:
        logger.warning("No existing Slack messages to update event count.")

    for response in messages:
        try:
            if response is None:
                continue

            # Update the event count in the plan block
            blocks = response["message"]["blocks"]
            plan = next((block for block in blocks if block["type"] == "plan"), None)

            plan["title"] = "Processing complete!"
            for i, task in enumerate(plan["tasks"]):
                if i == len(plan["tasks"]) - 1:
                    task["status"] = "error"
                else:
                    task["status"] = "complete"

            update_slack_message(slack_client, response, blocks)
        except Exception as e:
            logger.error(
                "Unexpected error occurred posting Slack error status update",
                extra={
                    "status_code": 500,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "error": traceback.format_exc(),
                    "e": e,
                },
            )


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event, context):
    """
    Main Lambda handler for a queue-service (S3-triggered) knowledge base synchronization
    """
    start_time = time.time()
    logger.info("log_event", extra=event)  # DELETE ME

    # Early validation of required configuration
    if not KNOWLEDGEBASE_ID or not DATA_SOURCE_ID:
        logger.error(
            "Missing required environment variables",
            extra={
                "status_code": 500,
                "knowledge_base_id": bool(KNOWLEDGEBASE_ID),
                "data_source_id": bool(DATA_SOURCE_ID),
            },
        )
        return {"statusCode": 500, "body": "Configuration error"}

    logger.info(
        "Starting knowledge base sync process",
        extra={
            "knowledge_base_id": KNOWLEDGEBASE_ID,
            "data_source_id": DATA_SOURCE_ID,
        },
    )

    slack_client = None
    slack_messages = []
    try:
        # Get events and update user channels
        records = event.get("Records", [])

        s3_records = []  # Track completed ingestion items

        # Process each S3 event record in the SQS batch
        for sqs_index, sqs_record in enumerate(records):
            try:
                if sqs_record.get("eventSource") != "aws:sqs":
                    event_time = sqs_record.get("attributes", {}).get("SentTimestamp", "Unknown")
                    logger.info("Event found", extra={"Event Trigger Time": event_time})
                    logger.warning(
                        "Skipping non-SQS event",
                        extra={
                            "event_source": sqs_record.get("eventSource"),
                            "record_index": sqs_index + 1,
                        },
                    )
                    continue

                body = json.loads(sqs_record.get("body", "{}"))
                s3_records += body.get("Records", [])

            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse SQS body: {str(e)}")
                continue

        # Check if the events are valid, and start syncing if so
        # Don't stop if not, let the lambda handle it.
        job_id = ""
        created = []
        deleted = []

        un_processed, process_key, bucket_name, is_new = get_unprocessed_files(s3_records)

        slack_client, slack_messages = initialise_slack_messages(len(s3_records), is_new)

        if not s3_records:
            logger.info("No valid S3 records to process", extra={"s3_records": len(records)})
        else:

            logger.info("Processing S3 records", extra={"record_count": len(s3_records)})
            success, job_id, created, deleted = process_s3_records(s3_records)

            if not success:
                msg = "Could not start sync process"
                logger.error(
                    msg,
                    extra={
                        "job_id": job_id,
                    },
                )
                return {"statusCode": 500, "body": msg, "job_id": job_id}

            # Update file messages in Slack (N removed, N added, etc)
            update_slack_files(
                slack_client=slack_client, created_files=created, deleted_files=deleted, messages=slack_messages
            )

        # Check length of session, even if we haven't started syncing
        total_duration = time.time() - start_time

        # Make sure all tasks are marked as complete in the Slack Plan
        if not un_processed:
            update_slack_complete(slack_client=slack_client, messages=slack_messages, feedback=None)

        set_unprocessed_files(
            s3_records=s3_records, unprocessed_files=un_processed, key=process_key, bucket=bucket_name
        )

        logger.info(
            "Knowledge base sync process completed",
            extra={
                "status_code": 200,
                "job_id": job_id,
                "trigger_files": created + deleted,
                "total_duration_ms": round(total_duration * 1000, 2),
                "knowledge_base_id": KNOWLEDGEBASE_ID,
                "next_steps": "Monitor Bedrock console for ingestion job completion status",
            },
        )

        return {
            "statusCode": 200,
            "body": (f"Successfully triggered ingestion job for {len(created) + len(deleted)} trigger file(s)",),
        }

    except ClientError as e:
        # Handle AWS service errors
        return handle_client_error(e, start_time, slack_client, slack_messages)

    except Exception as e:
        # Handle unexpected errors
        update_slack_error(slack_client=slack_client, messages=slack_messages)
        logger.error(
            "Unexpected error occurred",
            extra={
                "status_code": 500,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "error": traceback.format_exc(),
                "e": e,
            },
        )
        return {"statusCode": 500, "body": f"Unexpected error: {str(e)}"}
