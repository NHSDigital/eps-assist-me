import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from app.config import config
from app.services import converter
from app.services import s3_client

logger = Logger()


def process_s3_record(record: Dict[str, Any], record_index: int) -> Dict[str, str]:
    """
    converts or copies file from raw/ to processed/
    .md and .txt pass through, others convert to markdown
    """
    try:
        s3_info = record.get("s3", {})
        bucket_info = s3_info.get("bucket", {})
        object_info = s3_info.get("object", {})

        bucket_name = bucket_info.get("name")
        object_key = object_info.get("key")

        if not bucket_name or not object_key:
            logger.warning(f"Record {record_index}: Missing bucket or key information")
            return {"status": "skipped", "message": "Invalid S3 record"}

        logger.info(f"Processing: s3://{bucket_name}/{object_key}")

        file_path = Path(object_key)
        file_extension = file_path.suffix.lower()

        if not converter.is_supported_format(file_extension):
            logger.warning(f"Unsupported file type: {file_extension}")
            return {"status": "skipped", "message": f"Unsupported format: {file_extension}"}

        if object_key.startswith(config.RAW_PREFIX):
            relative_key = object_key[len(config.RAW_PREFIX) :]
        else:
            relative_key = object_key

        if converter.is_passthrough_format(file_extension):
            logger.info(f"Pass-through file: {file_extension}")
            output_key = f"{config.PROCESSED_PREFIX}{relative_key}"
            s3_client.copy_s3_object(bucket_name, object_key, bucket_name, output_key)
            return {"status": "success", "message": f"Copied to {output_key}"}

        if converter.is_convertible_format(file_extension):
            logger.info(f"Converting file: {file_extension}")

            # Create secure temporary directory
            temp_dir_path = tempfile.mkdtemp(prefix="preprocessing_")
            temp_dir = Path(temp_dir_path)

            try:
                input_path = temp_dir / file_path.name
                output_filename = file_path.stem + ".md"
                output_path = temp_dir / output_filename

                s3_client.download_from_s3(bucket_name, object_key, input_path)
                conversion_success = converter.convert_document_to_markdown(input_path, output_path)

                if not conversion_success:
                    logger.error(f"Conversion failed for {object_key}")
                    return {"status": "failed", "message": "Conversion failed"}

                output_key = f"{config.PROCESSED_PREFIX}{Path(relative_key).stem}.md"
                s3_client.upload_to_s3(output_path, bucket_name, output_key)

                logger.info(f"Successfully processed: {output_key}")
                return {"status": "success", "message": f"Converted to {output_key}"}

            finally:
                # Clean up entire temporary directory securely
                if temp_dir.exists():
                    shutil.rmtree(temp_dir_path, ignore_errors=True)

        return {"status": "skipped", "message": "Unknown processing path"}

    except Exception as e:
        logger.error(f"Error processing record {record_index}: {str(e)}")
        return {"status": "error", "message": str(e)}


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    triggered by s3 uploads to raw/
    converts documents to markdown for knowledge base ingestion
    """
    logger.info("Preprocessing function invoked")

    try:
        records = event.get("Records", [])

        if not records:
            logger.warning("No records in event")
            return {"statusCode": 200, "body": json.dumps({"message": "No records to process"})}

        logger.info(f"Processing {len(records)} record(s)")

        results = []
        for idx, record in enumerate(records):
            result = process_s3_record(record, idx)
            results.append(result)

        success_count = sum(1 for r in results if r["status"] == "success")
        failed_count = sum(1 for r in results if r["status"] == "failed")
        skipped_count = sum(1 for r in results if r["status"] == "skipped")

        logger.info(f"Processing complete: {success_count} success, {failed_count} failed, {skipped_count} skipped")

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Processing complete",
                    "total": len(records),
                    "success": success_count,
                    "failed": failed_count,
                    "skipped": skipped_count,
                    "results": results,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
