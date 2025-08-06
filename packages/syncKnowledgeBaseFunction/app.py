import os
import time
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger


# Initialize Powertools Logger with service name for better log organization
logger = Logger(service="syncKnowledgeBaseFunction")

# Initialize Bedrock client for knowledge base operations
bedrock_agent = boto3.client("bedrock-agent")


@logger.inject_lambda_context
def handler(event, context):
    """
    Lambda handler that processes S3 events and triggers Bedrock Knowledge Base ingestion.

    This function is triggered when documents are uploaded to the S3 bucket and automatically
    starts an ingestion job to update the knowledge base with new content.
    """
    # Record start time for performance tracking
    start_time = time.time()

    # Get required environment variables
    knowledge_base_id = os.environ.get("KNOWLEDGEBASE_ID")
    data_source_id = os.environ.get("DATA_SOURCE_ID")

    # Validate configuration
    if not knowledge_base_id or not data_source_id:
        logger.error(
            "Missing required environment variables",
            extra={
                "knowledge_base_id": bool(knowledge_base_id),
                "data_source_id": bool(data_source_id),
            },
        )
        return {"statusCode": 500, "body": "Configuration error"}

    logger.info(
        "Starting knowledge base sync process",
        extra={
            "knowledge_base_id": knowledge_base_id,
            "data_source_id": data_source_id,
        },
    )

    try:
        processed_files = []
        job_ids = []

        # Process each S3 event record
        for record_index, record in enumerate(event.get("Records", [])):
            if record.get("eventSource") == "aws:s3":
                # Validate S3 event structure
                s3_info = record.get("s3", {})
                bucket_name = s3_info.get("bucket", {}).get("name")
                object_key = s3_info.get("object", {}).get("key")

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

                # Extract S3 event details
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

                # Start ingestion job for the knowledge base
                ingestion_start_time = time.time()
                response = bedrock_agent.start_ingestion_job(
                    knowledgeBaseId=knowledge_base_id,
                    dataSourceId=data_source_id,
                    description=f"Auto-sync triggered by S3 event: {event_name} on {key}",
                )
                ingestion_request_time = time.time() - ingestion_start_time

                # Extract job information
                job_id = response["ingestionJob"]["ingestionJobId"]
                job_status = response["ingestionJob"]["status"]

                logger.info(
                    "Successfully started ingestion job",
                    extra={
                        "job_id": job_id,
                        "job_status": job_status,
                        "knowledge_base_id": knowledge_base_id,
                        "trigger_file": key,
                        "ingestion_request_duration_ms": round(ingestion_request_time * 1000, 2),
                        "note": "Job will process all files in data source, not just trigger file",
                    },
                )

                # Track processed files and job IDs for summary
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

        # Calculate total processing time
        total_duration = time.time() - start_time

        # Log successful completion summary
        logger.info(
            "Knowledge base sync process completed",
            extra={
                "statusCode": 200,
                "trigger_files_processed": len(processed_files),
                "ingestion_jobs_started": len(job_ids),
                "job_ids": job_ids,
                "trigger_files": processed_files,
                "total_duration_ms": round(total_duration * 1000, 2),
                "knowledge_base_id": knowledge_base_id,
                "next_steps": "Monitor Bedrock console for ingestion job completion status",
            },
        )

        # Log explicit success message for easy monitoring
        logger.info("Ingestion jobs triggered successfully - check Bedrock console for final results")

        return {
            "statusCode": 200,
            "body": (
                f"Successfully triggered {len(job_ids)} ingestion job(s) for {len(processed_files)} trigger file(s)",
            ),
        }

    except ClientError as e:
        # Handle AWS service errors with detailed logging
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        # Handling for ConflictException
        if error_code == "ConflictException":
            logger.warning(
                "Ingestion job already in progress",
                extra={
                    "status_code": 409,
                    "error_code": error_code,
                    "error_message": error_message,
                    "knowledge_base_id": knowledge_base_id,
                    "data_source_id": data_source_id,
                    "duration_ms": round((time.time() - start_time) * 1000, 2),
                    "recommendation": (
                        "This is normal when multiple files are uploaded quickly. "
                        "The running job will process all files."
                    ),
                },
            )
            return {
                "statusCode": 409,
                "body": "Ingestion job already in progress - files will be processed by existing job",
            }
        else:
            logger.error(
                "AWS service error occurred",
                extra={
                    "status_code": 500,
                    "error_code": error_code,
                    "error_message": error_message,
                    "knowledge_base_id": knowledge_base_id,
                    "data_source_id": data_source_id,
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
