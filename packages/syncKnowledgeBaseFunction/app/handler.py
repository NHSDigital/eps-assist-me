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
from app.config.config import KNOWLEDGEBASE_ID, DATA_SOURCE_ID, SUPPORTED_FILE_TYPES, get_bot_token, logger
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

bedrock_agent = boto3.client("bedrock-agent")


def is_supported_file_type(file_key):
    """
    Check if file type is supported for Bedrock Knowledge Base ingestion
    """
    return any(file_key.lower().endswith(ext) for ext in SUPPORTED_FILE_TYPES)


def process_s3_record(record, record_index):
    """
    Process a single S3 record and start ingestion job if valid

    Validates S3 record structure, checks file type support, and triggers
    Bedrock Knowledge Base ingestion for supported documents.
    """
    # Extract S3 event details
    s3_info = record.get("s3", {})
    bucket_name = s3_info.get("bucket", {}).get("name")
    object_key = s3_info.get("object", {}).get("key")

    # Skip malformed S3 records
    if not bucket_name or not object_key:
        logger.warning(
            "Skipping invalid S3 record",
            extra={
                "record_index": record_index + 1,
                "has_bucket": bool(bucket_name),
                "has_object_key": bool(object_key),
            },
        )
        return False, None, None

    # Skip unsupported file types to avoid unnecessary processing
    if not is_supported_file_type(object_key):
        logger.info(
            "Skipping unsupported file type",
            extra={
                "file_key": object_key,
                "supported_types": list(SUPPORTED_FILE_TYPES),
                "record_index": record_index + 1,
            },
        )
        return False, None, None

    # Extract additional event metadata for logging
    event_name = record["eventName"]
    object_size = s3_info.get("object", {}).get("size", "unknown")

    # Determine event type for proper handling
    is_delete_event = event_name.startswith("ObjectRemoved")
    is_create_event = event_name.startswith("ObjectCreated")

    # Determine event type based on S3 event name
    if is_delete_event:
        event_type = "DELETE"
    elif is_create_event:
        event_type = "CREATE"
    else:
        event_type = "OTHER"

    logger.info(
        "Processing S3 event",
        extra={
            "event_name": event_name,
            "event_type": event_type,
            "bucket": bucket_name,
            "key": object_key,
            "object_size_bytes": object_size,
            "is_delete_event": is_delete_event,
            "record_index": record_index + 1,
        },
    )

    # Start Bedrock ingestion job (processes ALL files in data source)
    # For delete events, this re-ingests remaining files and removes deleted ones from vector index
    ingestion_start_time = time.time()
    bedrock_agent = boto3.client("bedrock-agent")

    # Create descriptive message based on event type
    if is_delete_event:
        description = f"Auto-sync: File deleted ({object_key}) - Re-ingesting to remove from vector index"
    elif is_create_event:
        description = f"Auto-sync: File added/updated ({object_key}) - Adding to vector index"
    else:
        description = f"Auto-sync triggered by S3 {event_name} on {object_key}"

    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=KNOWLEDGEBASE_ID,
        dataSourceId=DATA_SOURCE_ID,
        description=description,
    )
    ingestion_request_time = time.time() - ingestion_start_time

    # Extract job details for tracking and logging
    job_id = response["ingestionJob"]["ingestionJobId"]
    job_status = response["ingestionJob"]["status"]

    note = "Job processes all files in data source, not just trigger file"
    if is_delete_event:
        note += " - Deleted files will be removed from vector index"
    elif is_create_event:
        note += " - New/updated files will be added to vector index"

    logger.info(
        "Successfully started ingestion job",
        extra={
            "job_id": job_id,
            "job_status": job_status,
            "knowledge_base_id": KNOWLEDGEBASE_ID,
            "trigger_file": object_key,
            "event_type": event_type,
            "is_delete_event": is_delete_event,
            "ingestion_request_duration_ms": round(ingestion_request_time * 1000, 2),
            "note": note,
        },
    )

    return True, object_key, job_id, event_type


def handle_client_error(e, start_time):
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
        return {
            "statusCode": 409,
            "body": "Files uploaded successfully - processing by existing ingestion job (no action required)",
        }
    else:
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


def post_message(slack_client, channel_id: str, blocks: list, text_fallback: str):
    """
    Posts the formatted message to a specific channel.
    """
    try:
        return slack_client.chat_postMessage(channel=channel_id, text=text_fallback, blocks=blocks)
    except SlackApiError as e:
        logger.error(f"Error posting to {channel_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error posting to {channel_id}: {str(e)}")
        return None


def initialise_slack_messages(event_count: int) -> tuple:
    """
    Send Slack notification summarizing the synchronization status
    """
    # Build blocks for Slack message
    message = "*My knowledge base has been updated!*"
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

    logger.info(f"Authenticated as bot user: {response.get('user_id', 'unknown')}", extra={"response": response})

    # Get Channels where the Bot is a member
    logger.info("Find bot channels...")
    target_channels = get_bot_channels(slack_client)

    if not target_channels:
        logger.warning("SKIPPING - Bot is not in any channels. No messages sent.")
        return slack_client, []

    # Broadcast Loop
    logger.info(f"Broadcasting to {len(target_channels)} channels...")

    responses = []
    for channel_id in target_channels:
        response = post_message(slack_client=slack_client, channel_id=channel_id, blocks=blocks, text_fallback=message)
        responses.append(response)

    logger.info("Broadcast complete.", extra={"responses": len(responses)})
    return slack_client, responses


def update_slack_message(slack_client, response, blocks):
    """
    Update the existing Slack message blocks with new information
    """
    channel_id = response["channel"]
    ts = response["ts"]

    try:
        slack_client.chat_update(channel=channel_id, ts=ts, blocks=blocks)
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
                {"type": "rich_text_section", "elements": [{"type": "text", "text": detail}]} for detail in details
            ],
        }

    if outputs:
        task["output"] = {
            "type:": "rich_text",
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
    status: Literal["in_progress", "completed"] = "in_progress",
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
            "type:": "rich_text",
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


def update_slack_events(slack_client, event_count: int, messages: list):
    """
    Update the event count in the existing Slack message blocks
    """
    if not messages:
        logger.warning("No existing Slack messages to update event count.")
        return

    for response in messages:
        if response is None:
            continue

        # Update the event count in the plan block
        blocks = response["message"]["blocks"]
        plan = next((block for block in blocks if block["type"] == "plan"), None)
        task = plan["tasks"][-1] if (plan and "tasks" in plan and plan["tasks"]) else None

        title = "Fetching changes"
        outputs = [f"Found {event_count} event(s)"]

        if task:
            plan = update_slack_task(plan=plan, task=task, title=title, outputs=outputs)
        else:
            create_task(plan=plan, title=title, outputs=outputs)

        update_slack_message(slack_client, response, blocks)


def update_slack_files(slack_client, processed_files: list, messages: list, complete=False):
    """
    Update the existing Slack message blocks with the count of processed files
    """
    if not messages:
        return

    if not processed_files:
        logger.warning("No processed files to update in Slack messages.")
        return

    logger.info(
        "Processing lack files Slack Notification",
        extra={"processed_files": processed_files, "messages": messages, "complete": complete},
    )
    added = sum(1 for f in processed_files if f["event_type"] == "CREATE")
    deleted = sum(1 for f in processed_files if f["event_type"] == "DELETE")

    logger.info(f"Processed {added} added/updated and {deleted} deleted file(s).")

    for response in messages:
        if response is None:
            continue

        # Update the event count in the plan block
        blocks = response["message"]["blocks"]
        plan = next((block for block in blocks if block["type"] == "plan"), None)
        task = plan["tasks"][-1] if plan and "tasks" in plan and plan["tasks"] else None

        # Task params
        title = "Processing file changes"
        status = "completed" if complete else "in_progress"
        details = [f"{val} {label} file(s)" for val, label in [(added, "new"), (deleted, "removed")] if val > 0]
        outputs = [f"Total files processed: {added + deleted}"]

        if task:
            plan = update_slack_task(plan=plan, task=task, status=status, title=title, details=details, outputs=outputs)
        else:
            create_task(plan=plan, title=title, details=details, outputs=outputs)

        update_slack_message(slack_client=slack_client, response=response, blocks=blocks)


def update_slack_complete(slack_client, messages):
    """
    Mark Slack Plan as complete
    """
    if not messages:
        logger.warning("No existing Slack messages to update event count.")
        return

    for response in messages:
        if response is None:
            continue

        # Update the event count in the plan block
        blocks = response["message"]["blocks"]
        plan = next((block for block in blocks if block["type"] == "plan"), None)

        plan["title"] = "Processing complete!"
        for i, task in plan["tasks"]:
            task["status"] = "completed"

        update_slack_message(slack_client, response, blocks)


def process_sqs_record(s3_record):
    """
    Process a single Simple Queue Service record and prepare processing
    of a S3 record.
    """
    processed_files = []  # Track successfully processed file keys
    job_ids = []  # Track started ingestion job IDs

    body = json.loads(s3_record.get("body", "{}"))

    s3_records = body.get("Records", [])

    if not s3_records:
        logger.warning("Skipping SQS event - no S3 events found.")
        return {"processed_files": [], "job_ids": []}

    for s3_index, s3_record in enumerate(s3_records):
        if s3_record.get("eventSource") == "aws:s3":
            # Process S3 event and start ingestion if valid
            success, file_key, job_id, event_type = process_s3_record(s3_record, s3_index)
            if success:
                processed_files.append({"file_key": file_key, "event_type": event_type})
                job_ids.append(job_id)
        else:
            # Skip non-S3 events
            logger.warning(
                "Skipping non-S3 event",
                extra={
                    "event_source": s3_record.get("eventSource"),
                    "record_index": s3_index + 1,
                },
            )

    return {"processed_files": processed_files, "job_ids": job_ids}


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event, context):
    """
    Main Lambda handler for a queue-service (S3-triggered) knowledge base synchronization
    """
    start_time = time.time()

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

    try:
        records = event.get("Records", [])
        processed_files = []  # Track successfully processed file keys
        job_ids = []  # Track started ingestion job IDs

        slack_client, slack_messages = initialise_slack_messages(len(records))
        skipped = 0
        # Process each S3 event record in the SQS batch
        for sqs_index, sqs_record in enumerate(records):
            try:
                if sqs_record.get("eventSource") != "aws:sqs":
                    logger.warning(
                        "Skipping non-SQS event",
                        extra={
                            "event_source": sqs_record.get("eventSource"),
                            "record_index": sqs_index + 1,
                        },
                    )
                    update_slack_events(
                        slack_client=slack_client, event_count=len(records) - skipped, messages=slack_messages
                    )
                    skipped += 1
                    continue

                logger.info("Processing SQS record", extra={"record_index": sqs_index + 1})
                results = process_sqs_record(sqs_record)

                logger.info("Processed", extra={"processed": results})
                processed_files.extend(results["processed_files"])
                job_ids.extend(results["job_ids"])

                update_slack_files(
                    slack_client=slack_client,
                    processed_files=processed_files,
                    messages=slack_messages,
                    complete=(sqs_index == len(records) - 1),
                )

            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse SQS body: {str(e)}")
                continue

        total_duration = time.time() - start_time

        update_slack_complete(slack_client=slack_client, messages=slack_messages)

        logger.info(
            "Knowledge base sync process completed",
            extra={
                "status_code": 200,
                "ingestion_jobs_started": len(job_ids),
                "job_ids": job_ids,
                "trigger_files": processed_files,
                "total_duration_ms": round(total_duration * 1000, 2),
                "knowledge_base_id": KNOWLEDGEBASE_ID,
                "next_steps": "Monitor Bedrock console for ingestion job completion status",
            },
        )

        return {
            "statusCode": 200,
            "body": (
                f"Successfully triggered {len(job_ids)} ingestion job(s) for {len(processed_files)} trigger file(s)",
            ),
        }

    except ClientError as e:
        # Handle AWS service errors
        return handle_client_error(e, start_time)

    except Exception as e:
        # Handle unexpected errors
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
