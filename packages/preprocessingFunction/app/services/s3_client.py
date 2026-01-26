import boto3
from pathlib import Path
from aws_lambda_powertools import Logger
from app.config.config import AWS_ACCOUNT_ID

logger = Logger(child=True)
s3_client = boto3.client("s3")


def download_from_s3(bucket: str, key: str, local_path: Path) -> None:
    logger.info(f"Downloading s3://{bucket}/{key} to {local_path}")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    s3_client.download_file(
        Bucket=bucket,
        Key=key,
        Filename=str(local_path),
        ExtraArgs={"ExpectedBucketOwner": AWS_ACCOUNT_ID} if AWS_ACCOUNT_ID else {},
    )
    logger.info(f"Downloaded {local_path.stat().st_size} bytes")


def upload_to_s3(local_path: Path, bucket: str, key: str) -> None:
    logger.info(f"Uploading {local_path} to s3://{bucket}/{key}")
    s3_client.upload_file(
        Filename=str(local_path),
        Bucket=bucket,
        Key=key,
        ExtraArgs={"ExpectedBucketOwner": AWS_ACCOUNT_ID} if AWS_ACCOUNT_ID else {},
    )
    logger.info(f"Uploaded {local_path.stat().st_size} bytes")


def copy_s3_object(source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> None:
    """server-side copy for passthrough files (.md, .txt)"""
    logger.info(f"Copying s3://{source_bucket}/{source_key} to s3://{dest_bucket}/{dest_key}")
    copy_source = {"Bucket": source_bucket, "Key": source_key}
    kwargs = {"CopySource": copy_source, "Bucket": dest_bucket, "Key": dest_key}
    if AWS_ACCOUNT_ID:
        kwargs["ExpectedBucketOwner"] = AWS_ACCOUNT_ID
    s3_client.copy_object(**kwargs)
    logger.info("Copy completed")
