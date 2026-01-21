import os
from aws_lambda_powertools import Logger

logger = Logger(service="syncKnowledgeBaseFunction")

# Environment variables
SLACK_BOT_TOKEN_PARAMETER = os.environ.get("SLACK_BOT_TOKEN_PARAMETER")
