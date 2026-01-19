import os

DOCS_BUCKET_NAME = os.environ.get("DOCS_BUCKET_NAME", "")
RAW_PREFIX = os.environ.get("RAW_PREFIX", "raw/")
PROCESSED_PREFIX = os.environ.get("PROCESSED_PREFIX", "processed/")
AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "")

CONVERTIBLE_FORMATS = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv"]
PASSTHROUGH_FORMATS = [".md", ".txt", ".html", ".json"]
SUPPORTED_FILE_TYPES = CONVERTIBLE_FORMATS + PASSTHROUGH_FORMATS
