import os
from aws_lambda_powertools import Logger

logger = Logger(service="createIndexFunction")

# Environment variables
AWS_REGION = os.getenv("AWS_REGION", "eu-west-2")
INDEX_NAME = os.environ.get("INDEX_NAME")
