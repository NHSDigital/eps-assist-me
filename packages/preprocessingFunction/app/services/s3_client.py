import boto3
from pathlib import Path
from aws_lambda_powertools import Logger

logger = Logger(child=True)
s3_client = boto3.client("s3")


def download_from_s3(bucket: str, key: str, local_path: Path) -> None:
    """
    Download a file from S3 to local filesystem.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        local_path: Local file path to save to
    """
    logger.info(f"Downloading s3://{bucket}/{key} to {local_path}")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    s3_client.download_file(bucket, key, str(local_path))
    logger.info(f"Downloaded {local_path.stat().st_size} bytes")


def upload_to_s3(local_path: Path, bucket: str, key: str) -> None:
    """
    Upload a file from local filesystem to S3.

    Args:
        local_path: Local file path to upload
        bucket: S3 bucket name
        key: S3 object key
    """
    logger.info(f"Uploading {local_path} to s3://{bucket}/{key}")
    s3_client.upload_file(str(local_path), bucket, key)
    logger.info(f"Uploaded {local_path.stat().st_size} bytes")


def copy_s3_object(source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> None:
    """
    Copy an object within S3 (for pass-through files).

    Args:
        source_bucket: Source S3 bucket name
        source_key: Source S3 object key
        dest_bucket: Destination S3 bucket name
        dest_key: Destination S3 object key
    """
    logger.info(f"Copying s3://{source_bucket}/{source_key} to s3://{dest_bucket}/{dest_key}")
    copy_source = {"Bucket": source_bucket, "Key": source_key}
    s3_client.copy_object(CopySource=copy_source, Bucket=dest_bucket, Key=dest_key)
    logger.info("Copy completed")
