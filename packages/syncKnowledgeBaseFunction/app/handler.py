"""
Lambda handler for automatic Bedrock Knowledge Base synchronization

Triggered by S3 events (PUT/POST/DELETE) to automatically ingest new or updated
documents into the Bedrock Knowledge Base. This ensures the AI assistant always
has access to the latest documentation for answering user queries.
"""

import time
import uuid
import boto3
import json
from botocore.exceptions import ClientError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config.config import KNOWLEDGEBASE_ID, DATA_SOURCE_ID, SUPPORTED_FILE_TYPES, get_bot_token, logger

bedrock_agent = boto3.client("bedrock-agent")


class SlackNotifier:
    """Encapsulates all Slack message formatting and updating logic (DRY)"""

    def __init__(self, client):
        self.client = client
        self.active_messages = []

    def get_bot_channels(self):
        try:
            channels = []
            for result in self.client.conversations_list(types=["private_channel", "public_channel"], limit=1000):
                channels.extend([c["id"] for c in result["channels"]])
            return channels
        except Exception as e:
            logger.error(f"Network error listing channels: {e}")
            return []

    def initialize_broadcast(self, event_count: int):
        target_channels = self.get_bot_channels()
        if not target_channels:
            return

        blocks = self._build_initial_blocks(event_count)

        for channel_id in target_channels:
            try:
                response = self.client.chat_postMessage(
                    channel=channel_id, text="Knowledge base syncing...", blocks=blocks
                )
                self.active_messages.append({"channel": channel_id, "ts": response["ts"], "blocks": blocks})
            except SlackApiError as e:
                logger.error(f"Error posting to {channel_id}: {e}")

    def update_progress(self, added: int, deleted: int, is_complete: bool = False):
        if not self.active_messages:
            return

        status = "completed" if is_complete else "in_progress"
        title = "Processing complete!" if is_complete else "Processing file changes..."
        details = [f"{val} {label} file(s)" for val, label in [(added, "new"), (deleted, "removed")] if val > 0]
        outputs = [f"Total files processed: {added + deleted}"]

        for msg in self.active_messages:
            plan = next((b for b in msg["blocks"] if b["type"] == "plan"), None)
            if plan:
                plan["title"] = title
                plan["status"] = status

                # Update or create the task
                if not plan.get("tasks"):
                    plan["tasks"] = [{"task_id": uuid.uuid4().hex}]

                task = plan["tasks"][0]
                task.update(
                    {
                        "title": title,
                        "status": status,
                        "details": self._build_rich_text(details),
                        "output": self._build_rich_text(outputs),
                    }
                )

            try:
                self.client.chat_update(channel=msg["channel"], ts=msg["ts"], blocks=msg["blocks"])
            except SlackApiError as e:
                logger.error(f"Error updating message: {e}")

    def _build_rich_text(self, items):
        return {
            "type": "rich_text",
            "block_id": uuid.uuid4().hex,
            "elements": [{"type": "rich_text_section", "elements": [{"type": "text", "text": i}]} for i in items],
        }

    def _build_initial_blocks(self, event_count):
        # Simplified initialization blocks
        return [
            {"type": "section", "text": {"type": "plain_text", "text": "I am syncing changes to my knowledge base."}},
            {
                "type": "plan",
                "plan_id": "plan_1",
                "title": "Fetching changes...",
                "tasks": [
                    {
                        "task_id": uuid.uuid4().hex,
                        "title": "Fetching changes",
                        "status": "in_progress",
                        "output": self._build_rich_text([f"Found {event_count} event(s)"]),
                    }
                ],
            },
        ]


def parse_s3_events(records):
    """Extracts valid files and event types from SQS/S3 records"""
    processed_files = []

    for sqs_record in records:
        if sqs_record.get("eventSource") != "aws:sqs":
            continue

        try:
            body = json.loads(sqs_record.get("body", "{}"))
            for s3_record in body.get("Records", []):
                s3_info = s3_record.get("s3", {})
                object_key = s3_info.get("object", {}).get("key", "")

                if not object_key or not any(object_key.lower().endswith(ext) for ext in SUPPORTED_FILE_TYPES):
                    continue

                event_name = s3_record.get("eventName", "")
                event_type = "DELETE" if event_name.startswith("ObjectRemoved") else "CREATE"
                processed_files.append({"key": object_key, "type": event_type})

        except (json.JSONDecodeError, AttributeError):
            continue

    return processed_files


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event, context):
    start_time = time.time()

    if not KNOWLEDGEBASE_ID or not DATA_SOURCE_ID:
        return {"statusCode": 500, "body": "Configuration error"}

    records = event.get("Records", [])
    if not records:
        return {"statusCode": 400, "body": "No records to process"}

    token = get_bot_token()
    slack_client = WebClient(token=token)
    slack = SlackNotifier(slack_client)
    slack.initialize_broadcast(len(records))

    # 2. Extract all valid files first
    processed_files = parse_s3_events(records)

    added_count = sum(1 for f in processed_files if f["type"] == "CREATE")
    deleted_count = sum(1 for f in processed_files if f["type"] == "DELETE")

    # 3. Handle Slack Notifications neatly
    slack.update_progress(added_count, deleted_count, is_complete=False)

    job_id = None

    # 4. Trigger Bedrock ONLY ONCE if there are actually valid files to process
    if processed_files:
        try:
            response = bedrock_agent.start_ingestion_job(
                knowledgeBaseId=KNOWLEDGEBASE_ID,
                dataSourceId=DATA_SOURCE_ID,
                description=f"Auto-sync: {len(processed_files)} file(s) changed.",
            )
            job_id = response["ingestionJob"]["ingestionJobId"]

        except ClientError as e:
            if e.response.get("Error", {}).get("Code") != "ConflictException":
                return {"statusCode": 500, "body": str(e)}
            logger.info(
                "Ingestion job already running. Skipping trigger.",
                extra={
                    "status_code": 409,
                    "duration_ms": round((time.time() - start_time) * 1000, 2),
                    "explanation": "Normal when multiple files uploaded quickly",
                },
            )

    # 5. Mark as complete
    slack.update_progress(added_count, deleted_count, is_complete=True)

    return {"statusCode": 200, "body": f"Processed {len(processed_files)} files. Job ID: {job_id}"}
