import traceback

from slack_sdk import WebClient
from app.core.config import bot_messages, get_logger

logger = get_logger()


def get_friendly_channel_name(channel_id: str, client: WebClient) -> str:
    friendly_channel_name = channel_id
    try:
        conversations_info_response = client.conversations_info(channel=channel_id)
        if conversations_info_response["ok"]:
            friendly_channel_name = conversations_info_response["channel"]["name"]
        else:
            logger.warning(
                "There was a problem getting the friendly channel name",
                extra={"conversations_info_response": conversations_info_response},
            )
    except Exception:
        logger.warning("There was an error getting the friendly channel name", extra={"error": traceback.format_exc()})
    return friendly_channel_name


def post_error_message(channel: str, thread_ts: str | None, client: WebClient) -> None:
    try:
        post_params = {"channel": channel, "text": bot_messages.ERROR_RESPONSE}
        if thread_ts:  # Only add thread_ts for channel threads, not DMs
            post_params["thread_ts"] = thread_ts
        client.chat_postMessage(**post_params)
    except Exception:
        logger.error("Failed to post error message", extra={"error": traceback.format_exc()})
