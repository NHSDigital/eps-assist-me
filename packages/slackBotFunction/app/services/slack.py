import traceback

from slack_sdk import WebClient
from app.core.config import get_logger


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
