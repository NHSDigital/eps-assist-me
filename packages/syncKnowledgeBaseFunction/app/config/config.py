import os
import json
import traceback
from functools import lru_cache
from typing import Tuple
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parameters import get_parameter

logger = Logger(service="syncKnowledgeBaseFunction")

# Environment variables
KNOWLEDGEBASE_ID = os.environ.get("KNOWLEDGEBASE_ID")
DATA_SOURCE_ID = os.environ.get("DATA_SOURCE_ID")
SLACK_BOT_TOKEN_PARAMETER = os.environ.get("SLACK_BOT_TOKEN_PARAMETER")
AWS_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID")
SQS_URL = os.environ.get("SQS_URL")
SLACK_BOT_ACTIVE = os.environ.get("SLACK_BOT_ACTIVE", False)
KNOWLEDGE_SYNC_STATE_TABLE = os.environ.get("KNOWLEDGE_SYNC_STATE_TABLE", False)

# Supported file types for Bedrock Knowledge Base ingestion
SUPPORTED_FILE_TYPES = {".pdf", ".txt", ".md", ".csv", ".doc", ".docx", ".xls", ".xlsx", ".html", ".json"}


def to_bool(value: str | None) -> bool:
    # 1. Handle None immediately
    if value is None:
        return False

    # 2. Normalize the string and check against "false" values
    # We include '0' as a string and the integer 0 just in case
    if str(value).lower() in ("false", "0", "none", "f", "n", "no"):
        return False

    # 3. Otherwise, check if the string has content
    return bool(value)


@lru_cache()
def get_bot_token() -> Tuple[str, str]:
    try:
        bot_token_raw = get_parameter(SLACK_BOT_TOKEN_PARAMETER, decrypt=True)

        if not bot_token_raw:
            raise ValueError("Missing required parameters from Parameter Store")

        bot_token_data = json.loads(bot_token_raw)
        bot_token = bot_token_data.get("token")

        if not bot_token:
            raise ValueError("Missing required parameters: token or secret in Parameter Store values")

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in Parameter Store: {e}")
    except Exception:
        logger.error("Configuration error", extra={"error": traceback.format_exc()})
        raise
    return bot_token


@lru_cache()
def get_bot_active() -> bool:
    is_active = os.environ.get("SLACK_BOT_ACTIVE", "false")
    return to_bool(is_active)
