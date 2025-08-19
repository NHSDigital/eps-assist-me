import os
from aws_lambda_powertools import Logger

logger = Logger(service="syncKnowledgeBaseFunction")

# Environment variables
KNOWLEDGEBASE_ID = os.environ.get("KNOWLEDGEBASE_ID")
DATA_SOURCE_ID = os.environ.get("DATA_SOURCE_ID")
