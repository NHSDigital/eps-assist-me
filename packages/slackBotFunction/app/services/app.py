from functools import lru_cache
import logging

from slack_bolt import App
from app.core.config import get_ssm_params
from app.slack.slack_handlers import setup_handlers
from aws_lambda_powertools import Logger


@lru_cache
def get_app(logger: Logger) -> App:
    bot_token, signing_secret = get_ssm_params()
    # pass the correct logger to slack bolt so it can be pickled correctly
    powertools_logger = logging.getLogger(name=logger.name)

    # initialise the Slack app
    app = App(
        process_before_response=True,
        token=bot_token,
        signing_secret=signing_secret,
        logger=powertools_logger,
    )
    setup_handlers(app)
    return app
