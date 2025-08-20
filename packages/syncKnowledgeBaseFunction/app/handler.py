"""
Lambda handler for syncing Bedrock Knowledge Base when S3 documents are uploaded/modified/deleted
"""

import time
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger
from app.config.config import KNOWLEDGEBASE_ID, DATA_SOURCE_ID

logger = Logger(service="syncKnowledgeBaseFunction")


def get_bedrock_agent():
    """Create Bedrock Agent client for knowledge base operations"""
    return boto3.client("bedrock-agent")


@logger.inject_lambda_context
def handler(event, context):
    """Lambda handler that processes S3 events and triggers Bedrock Knowledge Base ingestion."""
    start_time = time.time()

    # Validate required environment variables are configured
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
        processed_files = []  # Track files that triggered ingestion
        job_ids = []  # Track started ingestion job IDs

        # Process each S3 event record
        for record_index, record in enumerate(event.get("Records", [])):
            if record.get("eventSource") == "aws:s3":
                # Extract S3 bucket and object information
                s3_info = record.get("s3", {})
                bucket_name = s3_info.get("bucket", {}).get("name")
                object_key = s3_info.get("object", {}).get("key")

                # Skip records with missing S3 information
                if not bucket_name or not object_key:
                    logger.warning(
                        "Skipping invalid S3 record",
                        extra={
                            "record_index": record_index + 1,
                            "has_bucket": bool(bucket_name),
                            "has_object_key": bool(object_key),
                        },
                    )
                    continue

                bucket = bucket_name
                key = object_key
                event_name = record["eventName"]
                object_size = s3_info.get("object", {}).get("size", "unknown")

                logger.info(
                    "Processing S3 event",
                    extra={
                        "event_name": event_name,
                        "bucket": bucket,
                        "key": key,
                        "object_size_bytes": object_size,
                        "record_index": record_index + 1,
                        "total_records": len(event.get("Records", [])),
                    },
                )

                # Start Bedrock knowledge base ingestion job
                ingestion_start_time = time.time()
                bedrock_agent = get_bedrock_agent()
                response = bedrock_agent.start_ingestion_job(
                    knowledgeBaseId=KNOWLEDGEBASE_ID,
                    dataSourceId=DATA_SOURCE_ID,
                    description=f"Auto-sync triggered by S3 {event_name} on {key}",
                )
                ingestion_request_time = time.time() - ingestion_start_time

                job_id = response["ingestionJob"]["ingestionJobId"]
                job_status = response["ingestionJob"]["status"]

                logger.info(
                    "Successfully started ingestion job",
                    extra={
                        "job_id": job_id,
                        "job_status": job_status,
                        "knowledge_base_id": KNOWLEDGEBASE_ID,
                        "trigger_file": key,
                        "ingestion_request_duration_ms": round(ingestion_request_time * 1000, 2),
                        "note": "Job will process all files in data source, not just trigger file",
                    },
                )

                processed_files.append(key)
                job_ids.append(job_id)
            else:
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
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        # ConflictException means ingestion job already running - this is normal
        if error_code == "ConflictException":
            logger.warning(
                "Ingestion job already in progress - no action required",
                extra={
                    "status_code": 409,
                    "error_code": error_code,
                    "error_message": error_message,
                    "description": "Files uploaded successfully and will be processed by existing ingestion job",
                    "action_required": "none",
                    "knowledge_base_id": KNOWLEDGEBASE_ID,
                    "data_source_id": DATA_SOURCE_ID,
                    "duration_ms": round((time.time() - start_time) * 1000, 2),
                    "explanation": (
                        "This is normal when multiple files are uploaded quickly. "
                        "The running job will process all files."
                    ),
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
                    "knowledge_base_id": KNOWLEDGEBASE_ID,
                    "data_source_id": DATA_SOURCE_ID,
                    "duration_ms": round((time.time() - start_time) * 1000, 2),
                },
            )
            return {
                "statusCode": 500,
                "body": f"AWS error: {error_code} - {error_message}",
            }

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
