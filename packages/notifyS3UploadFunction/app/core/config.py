"""
Core configuration for the Slack bot.
Sets up all the AWS and Slack connections we need.
"""

from __future__ import annotations
from functools import lru_cache
import os
import json
import traceback
from typing import Tuple
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import utils
from aws_lambda_powertools.utilities.parameters import get_parameter

# we use lru_cache for lots of configs so they are cached


@lru_cache()
def get_logger() -> Logger:
    powertools_logger = Logger(service="debounceS3UploadFunction")
    utils.copy_config_to_registered_loggers(source_logger=powertools_logger, ignore_log_level=True)
    return powertools_logger


# set up logger as its used in other functions
logger = get_logger()


@lru_cache()
def get_ssm_params() -> Tuple[str, str]:
    bot_token_parameter = os.environ["SLACK_BOT_TOKEN_PARAMETER"]
    try:
        bot_token_raw = get_parameter(bot_token_parameter, decrypt=True)
        bot_token_data = json.loads(bot_token_raw)

        bot_token = bot_token_data.get("token")

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in Parameter Store: {e}")
    except Exception:
        logger.error("Configuration error", extra={"error": traceback.format_exc()})
        raise
    return bot_token


@lru_cache
def get_bot_token() -> str:
    bot_token, _ = get_ssm_params()
    return bot_token
