import time
from slack_bolt import App
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError
from app.slack.slack_events import trigger_async_processing

logger = Logger(service="slackBotFunction")

# Lazy initialization of Slack app
_app = None


def get_app():
    """Get or create the Slack app instance"""
    global _app
    if _app is None:
        from app.config.config import bot_token, signing_secret

        _app = App(
            process_before_response=True,
            token=bot_token,
            signing_secret=signing_secret,
        )
        _setup_handlers(_app)
    return _app


def _setup_handlers(app_instance):
    """Setup event handlers for the app"""
    from app.config.config import bot_token

    @app_instance.middleware
    def log_request(slack_logger, body, next):
        """Middleware to log incoming Slack requests using AWS Lambda Powertools logger."""
        logger.debug("Slack request received", extra={"body": body})
        return next()

    @app_instance.event("app_mention")
    def handle_app_mention(event, ack, body):
        """Handle when the bot is @mentioned"""
        ack()

        event_id = body.get("event_id")
        if not event_id:
            logger.warning("Missing event_id in Slack event body.")
        elif is_duplicate_event(event_id):
            logger.info(f"Duplicate event detected, skipping: {event_id}")
            return

        user_id = event.get("user", "unknown")
        logger.info(f"Processing @mention from user {user_id}", extra={"event_id": event_id})

        trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})

    @app_instance.event("message")
    def handle_direct_message(event, ack, body):
        """Handle direct messages to the bot"""
        ack()

        if event.get("channel_type") == "im":
            event_id = body.get("event_id")
            if not event_id:
                logger.warning("Missing event_id in Slack event body.")
            elif is_duplicate_event(event_id):
                logger.info(f"Duplicate event detected, skipping: {event_id}")
                return

            user_id = event.get("user", "unknown")
            logger.info(f"Processing DM from user {user_id}", extra={"event_id": event_id})

            trigger_async_processing({"event": event, "event_id": event_id, "bot_token": bot_token})


def is_duplicate_event(event_id):
    """Check if event has already been processed using conditional put"""
    from app.config.config import table

    try:
        ttl = int(time.time()) + 3600  # 1 hour TTL
        table.put_item(
            Item={"eventId": event_id, "ttl": ttl, "timestamp": int(time.time())},
            ConditionExpression="attribute_not_exists(eventId)",
        )
        return False  # Item didn't exist, so not a duplicate
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return True  # Item already exists, so it's a duplicate
        return False


# Create a module-level app instance that uses lazy loading
class AppProxy:
    def __getattr__(self, name):
        return getattr(get_app(), name)


app = AppProxy()
