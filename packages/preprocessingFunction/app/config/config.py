import os

DOCS_BUCKET_NAME = os.environ.get("DOCS_BUCKET_NAME", "")
RAW_PREFIX = os.environ.get("RAW_PREFIX", "raw/")
PROCESSED_PREFIX = os.environ.get("PROCESSED_PREFIX", "processed/")

# File types that should be converted to markdown
CONVERTIBLE_FORMATS = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv"]

# File types that should be passed through without conversion
PASSTHROUGH_FORMATS = [".md", ".txt", ".html", ".json"]

# All supported file types
SUPPORTED_FILE_TYPES = CONVERTIBLE_FORMATS + PASSTHROUGH_FORMATS
