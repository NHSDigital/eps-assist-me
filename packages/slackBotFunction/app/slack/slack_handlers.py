"""
Slack event handlers - handles @mentions and direct messages to the bot
"""

from functools import lru_cache
from slack_bolt import App
from app.core.config import get_bot_token, get_logger
from app.utils.handler_utils import is_duplicate_event, trigger_async_processing

logger = get_logger()


@lru_cache()
def setup_handlers(app: App):
    """
    Register all event handlers with the Slack app
    """

    @app.middleware
    def log_request(slack_logger, body, next):
        logger.debug("Slack request received", extra={"body": body})
        return next()

    @app.event("app_mention")
    def handle_app_mention(event, ack, body):
        """
        Handle @mentions in channels - when users mention the bot in a channel
        Acknowledges the event immediately and triggers async processing to avoid timeouts
        """
        ack()

        event_id = body.get("event_id")
        if not event_id or is_duplicate_event(event_id):
            logger.info("Skipping duplicate or missing event", extra={"event_id": event_id})
            return

        user_id = event.get("user", "unknown")
        logger.info("Processing @mention from user", extra={"user_id": user_id, "event_id": event_id})

        bot_token = get_bot_token()
        trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})

    @app.event("message")
    def handle_direct_message(event, ack, body):
        """
        Handle direct messages to the bot - private 1:1 conversations
        Filters out channel messages and processes only direct messages
        """
        ack()

        # Only handle DMs, ignore channel messages
        if event.get("channel_type") != "im":
            return

        event_id = body.get("event_id")
        if not event_id or is_duplicate_event(event_id):
            logger.info("Skipping duplicate or missing event", extra={"event_id": event_id})
            return

        user_id = event.get("user", "unknown")
        logger.info("Processing DM from user", extra={"user_id": user_id, "event_id": event_id})

        bot_token = get_bot_token()
        trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})
