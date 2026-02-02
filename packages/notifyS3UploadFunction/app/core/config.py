from dataclasses import dataclass
import json
import os
import traceback
from functools import lru_cache
from typing import Tuple
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parameters import get_parameter

logger = Logger(service="syncKnowledgeBaseFunction")


@lru_cache()
def get_bot_token() -> Tuple[str, str]:
    bot_token_parameter = os.environ["SLACK_BOT_TOKEN_PARAMETER"]
    try:
        bot_token_raw = get_parameter(bot_token_parameter, decrypt=True)

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


@dataclass
class SlackBotConfig:
    SLACK_BOT_TOKEN_PARAMETER: str
