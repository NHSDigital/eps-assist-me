"""
Lambda handler for automatic Bedrock Knowledge Base synchronization

Triggered by S3 events (PUT/POST/DELETE) to automatically ingest new or updated
documents into the Bedrock Knowledge Base. This ensures the AI assistant always
has access to the latest documentation for answering user queries.
"""

import time
import boto3
from botocore.exceptions import ClientError
from app.config.config import KNOWLEDGEBASE_ID, DATA_SOURCE_ID, SUPPORTED_FILE_TYPES, logger


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

    return True, object_key, job_id


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


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event, context):
    """
    Main Lambda handler for S3-triggered knowledge base synchronization
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
        processed_files = []  # Track successfully processed file keys
        job_ids = []  # Track started ingestion job IDs

        # Process each record in the Lambda event
        for record_index, record in enumerate(event.get("Records", [])):
            if record.get("eventSource") == "aws:s3":
                # Process S3 event and start ingestion if valid
                success, file_key, job_id = process_s3_record(record, record_index)
                if success:
                    processed_files.append(file_key)
                    job_ids.append(job_id)
            else:
                # Skip non-S3 events
                logger.warning(
                    "Skipping non-S3 event",
                    extra={
                        "event_source": record.get("eventSource"),
                        "record_index": record_index + 1,
                    },
                )

        total_duration = time.time() - start_time

        logger.info(
            "Knowledge base sync process completed",
            extra={
                "status_code": 200,
                "trigger_files_processed": len(processed_files),
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
            },
        )
        return {"statusCode": 500, "body": f"Unexpected error: {str(e)}"}
