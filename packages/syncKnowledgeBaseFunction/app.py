import os
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

# Configure logging
logger = Logger()

# Initialize Bedrock client
bedrock_agent = boto3.client("bedrock-agent")


@logger.inject_lambda_context
def handler(event, context):
    """
    Lambda handler for S3 events that triggers knowledge base ingestion.
    """
    knowledge_base_id = os.environ.get("KNOWLEDGEBASE_ID")
    data_source_id = os.environ.get("DATA_SOURCE_ID")

    if not knowledge_base_id or not data_source_id:
        logger.error("Missing required environment variables: KNOWLEDGEBASE_ID or DATA_SOURCE_ID")
        return {"statusCode": 500, "body": "Configuration error"}

    try:
        # Process S3 event records
        for record in event.get("Records", []):
            if record.get("eventSource") == "aws:s3":
                bucket = record["s3"]["bucket"]["name"]
                key = record["s3"]["object"]["key"]
                event_name = record["eventName"]

                logger.info(f"Processing S3 event: {event_name} for {bucket}/{key}")

                # Start ingestion job for the knowledge base
                response = bedrock_agent.start_ingestion_job(
                    knowledgeBaseId=knowledge_base_id,
                    dataSourceId=data_source_id,
                    description=f"Auto-sync triggered by S3 event: {event_name} on {key}",
                )

                job_id = response["ingestionJob"]["ingestionJobId"]
                logger.info(f"Started ingestion job {job_id} for knowledge base {knowledge_base_id}")

        return {"statusCode": 200, "body": "Ingestion triggered successfully"}

    except ClientError as e:
        logger.error(f"AWS service error: {e}")
        return {"statusCode": 500, "body": f"AWS error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"statusCode": 500, "body": f"Error: {str(e)}"}
