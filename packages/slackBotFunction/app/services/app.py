from functools import lru_cache

from slack_bolt import App
from app.core.config import get_ssm_params
from app.core.config import get_logger
from app.slack.slack_handlers import setup_handlers

logger = get_logger()


@lru_cache()
def get_app():
    bot_token, signing_secret = get_ssm_params()

    # initialise the Slack app
    app = App(
        process_before_response=True,
        token=bot_token,
        signing_secret=signing_secret,
        logger=logger,
    )
    setup_handlers(app)
    return app
