"""
Lambda handler for automatic Bedrock Knowledge Base synchronization

Triggered by S3 events (PUT/POST/DELETE) to automatically ingest new or updated
documents into the Bedrock Knowledge Base. This ensures the AI assistant always
has access to the latest documentation for answering user queries.
"""

import json
import time
import traceback
import uuid
import boto3
from typing import Literal
from app.config.config import (
    KNOWLEDGEBASE_ID,
    DATA_SOURCE_ID,
    SUPPORTED_FILE_TYPES,
    SQS_URL,
    SLACK_BOT_ACTIVE,
    get_bot_token,
    logger,
)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web import SlackResponse

bedrock_agent = boto3.client("bedrock-agent")
sqs = boto3.client("sqs")


class S3EventResult:
    file_name: str
    event_type: str
    processing: bool

    def __init__(self, file_name, event_type, processing):
        self.file_name = file_name
        self.event_type = event_type
        self.processing = processing


class SlackHandler:

    def __init__(self, silent=True):
        self.silent: bool = silent
        self.fetching_block_id: str = uuid.uuid4().hex
        self.update_block_id: str = uuid.uuid4().hex
        self.slack_client: WebClient | None = None
        self.messages: list[SlackResponse] = []
        self.default_slack_message: str = "Updating Source Files"

    def post_message(self, channel_id: str, blocks: list, text_fallback: str):
        """Send a new message to Slack"""
        try:
            if self.silent:
                logger.info(f"[SILENT MODE] Would have posted to {channel_id}")
                return {"ok": True, "channel": channel_id, "ts": "123456", "message": {"blocks": blocks}}

            return self.slack_client.chat_postMessage(channel=channel_id, text=text_fallback, blocks=blocks)
        except SlackApiError as e:
            logger.error(f"Error posting to {channel_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error posting to {channel_id}: {str(e)}")
            return None

    def update_message(self, channel_id: str, ts: str, blocks: list):
        """Update an existing Slack Message"""
        try:
            if self.silent:
                logger.info(f"[SILENT MODE] Would have posted to {channel_id}")
                return {"ok": True, "channel": channel_id, "ts": ts, "message": {"blocks": blocks}}

            return self.slack_client.chat_update(
                channel=channel_id, ts=ts, blocks=blocks, text=self.default_slack_message
            )
        except Exception as e:
            logger.error(f"Error posting to {channel_id}: {str(e)}")

    def create_task(
        self,
        id,
        title,
        plan=None,
        details=None,
        outputs=None,
        status: Literal["in_progress", "complete"] = "in_progress",
    ):
        """Create a new Slack Block Task for a Plan block"""
        task = {
            "task_id": id,
            "title": title,
            "status": status,
            "details": {
                "type": "rich_text",
                "block_id": uuid.uuid4().hex,
                "elements": [
                    {"type": "rich_text_section", "elements": [{"type": "text", "text": detail}]}
                    for detail in (details if details else [])
                ],
            },
            "output": {
                "type": "rich_text",
                "block_id": uuid.uuid4().hex,
                "elements": [
                    {"type": "rich_text_section", "elements": [{"type": "text", "text": output}]}
                    for output in (outputs if outputs else [])
                ],
            },
        }

        if plan:
            plan["title"] = f"{title}..."
            plan["status"] = status
            plan["tasks"] += [task]
        return task

    def update_task(
        self, id: str, message: str, status: Literal["in_progress", "completed"] = "in_progress", replace=False
    ):
        # Add header
        for slack_message in self.messages:
            channel_id = slack_message["channel"]
            ts = slack_message["ts"]

            if self.slack_client is None or slack_message is None:
                logger.warning("No Slack client or message, skipping update task")

            blocks = slack_message["message"]["blocks"]
            plan = next((block for block in blocks if block["type"] == "plan"), None)
            tasks = plan["tasks"]

            if tasks is None:
                logger.warning("No task found, skipping update task")

            task = next((task for task in tasks if task["task_id"] == id), None)
            if task is None:
                logger.warning(f"Could not find task with task_id {id}, skipping update task")

            details = task["details"]
            detail_elements = details["elements"] if not replace else []
            detail_elements.append({"type": "rich_text_section", "elements": [{"type": "text", "text": message}]})

            task["status"] = status
            task["details"] = details

            self.update_message(channel_id=channel_id, ts=ts, blocks=blocks)

    def get_bot_channels(self) -> list[str]:
        """
        Fetches all public and private channels the bot is a member of.
        """
        channel_ids = []
        try:
            for result in self.slack_client.conversations_list(types=["private_channel"], limit=1000):
                for channel in result["channels"]:
                    channel_ids.append(channel["id"])
        except Exception as e:
            logger.error(f"Network error listing channels: {str(e)}")
            return []

        return channel_ids

    def initialise_slack_messages(self):
        """
        Create a new slack message to inform user of SQS event process progress
        """
        try:
            # Build blocks for Slack message
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": "I am currently syncing changes to my knowledge base.\n This may take a few minutes.",
                    },
                },
                {
                    "type": "plan",
                    "plan_id": uuid.uuid4().hex,
                    "title": "Processing File Changes...",
                    "tasks": [
                        self.create_task(
                            id=self.fetching_block_id,
                            title="Fetching changes",
                            details=[],
                            outputs=["Searching"],
                            status="complete",
                        ),
                        self.create_task(
                            id=self.update_block_id,
                            title="Processing File Changes",
                            details=[],
                            outputs=["Initialising"],
                            status="in_progress",
                        ),
                    ],
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "plain_text", "text": "Please wait up-to 10 minutes for changes to take effect"}
                    ],
                },
            ]

            # Create new client
            token = get_bot_token()
            slack_client = WebClient(token=token)
            response = slack_client.auth_test()
            user_id = response.get("user_id", "unknown")

            self.slack_client = slack_client

            logger.info(f"Authenticated as bot user: {user_id}", extra={"response": response})

            # Get Channels where the Bot is a member
            logger.info("Find bot channels...")
            target_channels = self.get_bot_channels()

            if not target_channels:
                logger.warning("SKIPPING - Bot is not in any channels. No messages sent.")
                return

            # Broadcast Loop
            logger.info(f"Broadcasting to {len(target_channels)} channels...")

            responses = []
            for channel_id in target_channels:
                try:
                    logger.info("Creating new Slack Message")
                    response = self.post_message(
                        channel_id=channel_id,
                        blocks=blocks,
                        text_fallback="*My knowledge base has been updated!*",
                    )

                    if not response or not response.get("ok"):
                        logger.error("Error initialising Slack Message.", extra={"response": response})
                        continue

                    responses.append(response)
                except Exception as e:
                    logger.error(
                        f"Failed to initialise slack message for channel: {channel_id}", extra={"exception": e}
                    )
                    continue

            logger.info("Broadcast complete.", extra={"responses": len(responses)})
            self.messages = responses

        except Exception as e:
            logger.error(f"Failed to initialise slack messages: {str(e)}")

    def complete_plan(self):
        """Finish Slack Plan message block"""
        logger.info("Completing Plan")
        for slack_message in self.messages:
            try:
                if self.slack_client is None or slack_message is None:
                    logger.warning("No Slack client or message, skipping complete task")
                    continue

                channel_id = slack_message["channel"]
                ts = slack_message["ts"]

                # Update the event count in the plan block
                blocks = slack_message["message"]["blocks"]
                plan = next((block for block in blocks if block["type"] == "plan"), None)

                plan["title"] = "Processing complete!"
                for i, task in enumerate(plan["tasks"]):
                    task["status"] = "complete"

                self.update_message(channel_id=channel_id, ts=ts, blocks=blocks)
            except Exception as e:
                logger.error(
                    "Unexpected error occurred completing Slack message",
                    extra={
                        "status_code": 500,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "error": traceback.format_exc(),
                        "e": e,
                    },
                )


class S3EventHandler:
    @staticmethod
    def is_supported_file_type(file_key):
        """
        Check if file type is supported for Bedrock Knowledge Base ingestion
        """
        return any(file_key.lower().endswith(ext) for ext in SUPPORTED_FILE_TYPES)

    @staticmethod
    def validate_s3_event(bucket_name, object_key):
        logger.info(f"validate_s3_event {bucket_name}, {object_key}")
        if not bucket_name or not object_key:
            logger.warning(
                "Skipping invalid S3 record",
                extra={
                    "has_bucket": bool(bucket_name),
                    "has_object_key": bool(object_key),
                },
            )
            return False

        if not S3EventHandler.is_supported_file_type(object_key):
            logger.info(
                "Skipping unsupported file type",
                extra={"file_key": object_key, "supported_types": list(SUPPORTED_FILE_TYPES)},
            )
            return False
        return True

    @staticmethod
    def process_single_s3_event(record) -> S3EventResult:
        """Process single S3 event from SQS"""
        s3_info = record.get("s3", {})
        bucket_name = s3_info.get("bucket", {}).get("name")
        object_key = s3_info.get("object", {}).get("key")
        event_name = record.get("eventName", "Unknown")

        result = S3EventResult(file_name=object_key, event_type=event_name, processing=False)

        # Skip invalid records
        if not S3EventHandler.validate_s3_event(bucket_name, object_key):
            return result

        # Extract additional event metadata for logging
        event_name = record["eventName"]
        object_size = s3_info.get("object", {}).get("size", "unknown")

        logger.info(
            "Found valid S3 event for processing",
            extra={
                "event_name": event_name,
                "bucket": bucket_name,
                "key": object_key,
                "object_size_bytes": object_size,
            },
        )

        try:
            response = bedrock_agent.start_ingestion_job(
                knowledgeBaseId=KNOWLEDGEBASE_ID,
                dataSourceId=DATA_SOURCE_ID,
                description=f"Sync: {bucket_name}",
            )

            job_id = response["ingestionJob"]["ingestionJobId"]
            job_status = response["ingestionJob"]["status"]
            result.processing = True

            logger.info(
                "Successfully started ingestion job",
                extra={
                    "job_id": job_id,
                    "job_status": job_status,
                    "trigger_file": object_key,
                },
            )
        except Exception as e:
            logger.error(f"Error starting ingestion: {str(e)}")
            result.processing = False

        return result

    @staticmethod
    def process_multiple_sqs_events(slack_handler: SlackHandler, sqs_records):
        """Handle multiple individual events from SQS"""
        results = []
        for record in sqs_records:
            if record.get("eventSource") != "aws:sqs":
                logger.warning(
                    "Skipping non-SQS event",
                    extra={"event_source": record.get("eventSource")},
                )
                continue

            body = json.loads(record.get("body", {}))
            for s3_record in body.get("Records", []):
                result = S3EventHandler.process_single_s3_event(s3_record)
                results.append(result)

        return results

    @staticmethod
    def process_multiple_s3_events(slack_handler: SlackHandler, results):
        logger.info("Processing SQS record")

        counts = [
            ("created", len([result for result in results if result.event_type == "ObjectCreated"])),
            ("modified", len([result for result in results if result.event_type == "ObjectModified"])),
            ("deleted", len([result for result in results if result.event_type == "ObjectRemoved"])),
        ]

        # Generate the list only for non-zero values
        message_list = [f"{count} files {action}" for action, count in counts if count > 0]
        for message in message_list:
            slack_handler.update_task(id=slack_handler.update_block_id, message=message)

    @staticmethod
    def process_batched_queue_events(slack_handler: SlackHandler, events: list):
        """Handle collection of batched queue events"""
        processed_files = 0

        for event in events:
            s3_records = event.get("Records", [])

            if not s3_records:
                logger.warning("No records in event")
                continue

            logger.info(f"Processing {len(s3_records)} record(s)")
            slack_handler.update_task(
                id=slack_handler.fetching_block_id, message=f"Found {len(s3_records)} records", replace=True
            )

            result = S3EventHandler.process_multiple_sqs_events(slack_handler, s3_records)
            processed_files += len(result)

        logger.info(f"Completed {processed_files} file(s)")

    @staticmethod
    def close_sqs_events(events):
        logger.info(f"Closing {len(events)} sqs events")
        for event in events:
            try:
                sqs.delete_message(QueueUrl=SQS_URL, ReceiptHandle=event["ReceiptHandle"])
                logger.info("Successfully deleted sqs message from queue")
            except Exception as e:
                logger.error("Failed to delete sqs message from queue", extra={"Exception": e})

    @staticmethod
    def search_sqs_for_events():
        logger.info("Searching for new events")
        response = sqs.receive_message(QueueUrl=SQS_URL, MaxNumberOfMessages=10, WaitTimeSeconds=5)

        events = []
        messages = response.get("Messages", [])
        if not messages:
            logger.warning("No messages found")
            return events

        logger.info(f"Found {len(messages)} messages in SQS")
        for message in messages:
            body = message.get("Body", {})
            message_events = json.loads(body)
            if message_events:
                events.append(message_events)

        logger.info(f"Found {len(messages)} total event(s) in SQS messages")
        return events


def search_and_process_sqs_events(event):
    """
    Check if there are waiting SQS events.
    While SQS keep appearing, keep looking - limit to 20 iterations.
    """
    events = [event]
    loop_count = 20

    slack_handler = SlackHandler(silent=SLACK_BOT_ACTIVE)
    slack_handler.initialise_slack_messages()

    for i in range(loop_count):
        logger.info(f"Starting process round {i + 1}")
        # If there are no events, stop
        if not events:
            break

        # Delete sqs events that we have polled
        # The initial event will cancel with the success of the lambda
        if i > 0:
            S3EventHandler.close_sqs_events(events)

        S3EventHandler.process_batched_queue_events(slack_handler, events)

        # Search for any events in the sqs queue
        events = S3EventHandler.search_sqs_for_events()

    slack_handler.complete_plan()


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event, context):
    """
    Main Lambda handler for a queue-service (S3-triggered) knowledge base synchronization
    """
    start_time = time.time()
    logger.info("log_event", extra=event)

    if not KNOWLEDGEBASE_ID or not DATA_SOURCE_ID:
        logger.exception(
            "Missing required environment variables",
            extra={
                "status_code": 500,
                "knowledge_base_id": bool(KNOWLEDGEBASE_ID),
                "data_source_id": bool(DATA_SOURCE_ID),
            },
        )
        return {"statusCode": 500, "body": "Configuration error"}

    logger.info(
        "Starting knowledge base sync process",
        extra={
            "knowledge_base_id": KNOWLEDGEBASE_ID,
            "data_source_id": DATA_SOURCE_ID,
        },
    )

    try:
        search_and_process_sqs_events(event)

        total_duration = time.time() - start_time
        logger.info("Completed search and processing of sqs events", extra={"process_time": total_duration})
        return {
            "statusCode": 200,
            "body": ("Successfully polled and processed sqs events"),
        }
    except Exception as e:
        # Handle unexpected errors
        logger.error(
            "Unexpected error occurred",
            extra={
                "status_code": 500,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "error": traceback.format_exc(),
            },
        )
        return {"statusCode": 500, "body": f"Unexpected error: {str(e)}"}
