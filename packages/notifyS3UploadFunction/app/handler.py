"""
Lambda handler for notifying Slack channels of S3 uploads
"""

from app.core.config import get_logger, get_ssm_params
from aws_lambda_powertools.utilities.typing import LambdaContext
import json
import urllib.request


logger = get_logger()


def get_bot_channels(slack_token):
    """
    Fetches all public and private channels the bot is a member of.
    Handles pagination for bots in >100 channels.
    """
    url = "https://slack.com/api/users.conversations"
    channel_ids = []
    next_cursor = None

    while True:
        params = {"types": "public_channel,private_channel", "limit": 200, "exclude_archived": "true"}
        if next_cursor:
            params["cursor"] = next_cursor

        query_string = urllib.parse.urlencode(params)
        req = urllib.request.Request(f"{url}?{query_string}", method="GET")
        req.add_header("Authorization", f"Bearer {slack_token}")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req) as response:
                res_body = json.loads(response.read().decode("utf-8"))

                if not res_body.get("ok"):
                    logger.error(f"Error fetching channels: {res_body.get('error')}")
                    return []

                for channel in res_body.get("channels", []):
                    channel_ids.append(channel["id"])

                next_cursor = res_body.get("response_metadata", {}).get("next_cursor")
                if not next_cursor:
                    break
        except Exception as e:
            logger.error(f"Network error listing channels: {str(e)}")
            return []

    return channel_ids


def post_message(slack_token, channel_id, blocks, text_fallback):
    """
    Posts the formatted message to a specific channel.
    """
    url = "https://slack.com/api/chat.postMessage"
    payload = {"channel": channel_id, "text": text_fallback, "blocks": blocks}

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {slack_token}")

    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            if not res.get("ok"):
                logger.error(f"Failed to post to {channel_id}: {res.get('error')}")
                return False
            return True
    except Exception as e:
        logger.error(f"Error posting to {channel_id}: {str(e)}")
        return False


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Expects a batch of S3 event records via SQS.
    Parses the records, deduplicates file uploads, constructs a summary message,
    and broadcasts it to all Slack channels the bot is a member of.
    """
    bot_token = get_ssm_params()
    default_error = {"status": "false", "processed_files": 0, "channels_notified": 0}

    if not bot_token:
        logger.error("SLACK_BOT_TOKEN_PARAMETER environment variable is missing.")
        return default_error

    uploaded_files = []

    # Parse SQS Records (Your existing logic)
    for sqs_record in event.get("Records", []):
        try:
            s3_event_body = json.loads(sqs_record["body"])
            for s3_record in s3_event_body.get("Records", []):
                bucket_name = s3_record["s3"]["bucket"]["name"]
                file_key = s3_record["s3"]["object"]["key"]
                file_key = urllib.parse.unquote_plus(file_key)
                uploaded_files.append(f"• *{file_key}* (in `{bucket_name}`)")
        except Exception as e:
            logger.error(f"Error parsing record: {e}")
            continue

    # Find unique uploads
    unique_files = list(set(uploaded_files))
    if not unique_files:
        logger.info("No valid S3 records found in this batch.")
        return default_error

    # Build blocks for Slack message
    max_display = 10
    success_count = 0
    total_count = len(unique_files)
    display_list = unique_files[:max_display]
    more_count = total_count - max_display

    message_text = f"📄 *{total_count} New Document(s) Uploaded*:\n" + "\n".join(display_list)
    if more_count > 0:
        message_text += f"\n...and {more_count} more."

    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": message_text}}]

    # Get Channels where the Bot is a member
    logger.info("Find bot channels...")
    target_channels = get_bot_channels(bot_token)

    if not target_channels:
        logger.warning("Bot is not in any channels. No messages sent.")
        return {"status": "false", "processed_files": total_count, "channels_notified": success_count}

    # Broadcast Loop
    logger.info(f"Broadcasting to {len(target_channels)} channels...")

    for channel_id in target_channels:
        if post_message(bot_token, channel_id, blocks, "S3 Update Detected"):
            success_count += 1

    logger.info(f"Broadcast complete. Success: {success_count}/{len(target_channels)}")

    return {"status": "success", "processed_files": total_count, "channels_notified": success_count}
