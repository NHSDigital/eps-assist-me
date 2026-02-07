"""
Lambda handler for notifying Slack channels of S3 uploads
"""

from app.core.config import get_bot_on_prs, get_bot_token, logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import json
import urllib.request


def get_bot_channels(client):
    """
    Fetches all public and private channels the bot is a member of.
    """
    channel_ids = []
    try:
        for result in client.conversations_list(types=["private_channel"], limit=1000):
            for channel in result["channels"]:
                channel_ids.append(channel["id"])
    except Exception as e:
        logger.error(f"Network error listing channels: {str(e)}")
        return []

    return channel_ids


def post_message(client, channel_id, blocks, text_fallback):
    """
    Posts the formatted message to a specific channel.
    """
    try:
        client.chat_postMessage(channel=channel_id, text=text_fallback, blocks=blocks)
        return True
    except SlackApiError as e:
        logger.error(f"Error posting to {channel_id}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error posting to {channel_id}: {str(e)}")
        return False


def process_records(s3_event_body):
    """
    Processes S3 event records to extract uploaded file names,
    ignoring PR buckets if configured.
    """
    uploaded_files = []
    try:
        for s3_record in s3_event_body.get("Records", []):
            bucket_name = s3_record["s3"].get("bucket", {}).get("name", None)

            run_on_pr = get_bot_on_prs()
            if bucket_name is None:
                # Ignore PR buckets
                logger.info("Cannot find bucket name in record, skipping.")
                continue
            elif not run_on_pr and "pr-" in bucket_name:
                logger.info(f'Skipping notification for PR bucket "{bucket_name}"')
                continue

            file_key = s3_record["s3"]["object"]["key"]
            file_key = urllib.parse.unquote_plus(file_key)
            file_key = file_key.split("/")[-1]
            uploaded_files.append(f"\t - *{file_key}*")
    except Exception as e:
        logger.error(f"Error processing records: {str(e)}")

    return uploaded_files


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Expects a batch of S3 event records via SQS.
    Parses the records, deduplicates file uploads, constructs a summary message,
    and broadcasts it to all Slack channels the bot is a member of.
    """
    default_error = {"status": "failed", "processed_files": 0, "channels_notified": 0}
    uploaded_files = []

    # Parse SQS Records
    for sqs_record in event.get("Records", []):
        logger.info(f"Processing SQS record ID: {sqs_record.get('messageId', 'unknown')}")
        try:
            s3_event_body = json.loads(sqs_record["body"])
            result = process_records(s3_event_body)
            uploaded_files.extend(result)
        except SlackApiError as e:
            logger.error(f"Error parsing record: {e}")
        except Exception as e:
            logger.error(f"Error parsing record: {e}")

    # Find unique uploads
    unique_files = list(set(uploaded_files))
    if not unique_files:
        logger.info("No valid S3 records found in this batch.")
        return {**default_error, "status": "skipped"}

    # Build blocks for Slack message
    max_display = 10
    total_count = len(unique_files)
    display_list = unique_files[:max_display]
    more_count = total_count - max_display

    message_text = f":page_facing_up: *{total_count} New Document(s) Uploaded*:\n" + "\n".join(display_list)
    if more_count > 0:
        message_text += f"\n...and {more_count} more."

    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": message_text}}]

    # Create new client
    token = get_bot_token()
    client = WebClient(token=token)
    response = client.auth_test()

    logger.info(f"Authenticated as bot user: {response.get('user_id', 'unknown')}", extra={"response": response})

    # Get Channels where the Bot is a member
    logger.info("Find bot channels...")
    target_channels = get_bot_channels(client)

    success_count = 0
    if not target_channels:
        logger.warning("Bot is not in any channels. No messages sent.")
        return {"status": "failed", "processed_files": total_count, "channels_notified": success_count}

    # Broadcast Loop
    logger.info(f"Broadcasting to {len(target_channels)} channels...")

    for channel_id in target_channels:
        if post_message(client, channel_id, blocks, "S3 Update Detected"):
            success_count += 1

    logger.info(f"Broadcast complete. Success: {success_count}/{len(target_channels)}")

    return {"status": "success", "processed_files": total_count, "channels_notified": success_count}
