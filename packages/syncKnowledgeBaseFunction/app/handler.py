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
    KNOWLEDGE_SYNC_STATE_TABLE,
    get_bot_active,
    get_bot_token,
    logger,
)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web import SlackResponse
from functools import cached_property
from botocore.exceptions import ClientError

bedrock_agent = boto3.client("bedrock-agent")
sqs = boto3.client("sqs")

TaskStatus = Literal["in_progress", "complete"]


class DynamoDbHandler:
    @cached_property
    def table(self):
        # This will only run once per instance of SlackActivityDB
        print("Connecting to DynamoDB...")
        dynamodb = boto3.resource("dynamodb")
        return dynamodb.Table(KNOWLEDGE_SYNC_STATE_TABLE)

    def save_message(self, user_id, channel_id, ts):
        """Saves a new message with default counters set to 0."""
        return self.update_message(user_id, channel_id, ts, 0, 0, 0)

    def update_message(self, user_id, channel_id, ts, created, modified, deleted):
        """Updates an existing message or creates one with specific counters."""
        item = {
            "user_channel_composite": f"{user_id}#{channel_id}",
            "user_id": user_id,
            "channel_id": channel_id,
            "last_ts": str(ts),
            "created": created,
            "modified": modified,
            "deleted": deleted,
        }

        try:
            self.table.put_item(Item=item)
            logger.info(f"Successfully processed ts {ts} for user {user_id} in {channel_id}")
        except ClientError as e:
            logger.error(f"Failed to save to DynamoDB: {e.response['Error']['Message']}")

    def get_sync_state(self, user_id, channel_id):
        """
        Retrieves the latest message timestamp for a user in a specific channel.
        Returns the timestamp as a string, or None if no record exists.
        """
        try:
            response = self.table.get_item(Key={"user_channel_composite": f"{user_id}#{channel_id}"})

            items = response.get("Items")
            if not items:
                logger.info(f"No previous record for {user_id} in {channel_id}")
                return None

            latest_item = items[0]
            logger.info("Found latest item", extra={"ts": latest_item.get("last_ts")})
            return latest_item

        except ClientError as e:
            logger.error(f"DynamoDB Query Error: {e.response['Error']['Message']}")
            return None


class SlackHandler:

    def __init__(self, silent=True):
        self.silent: bool = silent
        if self.silent:
            logger.warning("Slack has been set to SILENT mode")

        self.fetching_block_id: str = uuid.uuid4().hex
        self.update_block_id: str = uuid.uuid4().hex
        self.slack_client: WebClient | None = None
        self.messages: list[SlackResponse] = []
        self.default_slack_message: str = "Updating Source Files"
        self.db_handler = DynamoDbHandler()
        self.target_channels = []

    def post_message(self, channel_id: str, blocks: list, text_fallback: str):
        """Send a new message to Slack"""
        try:
            if self.silent:
                mock_ts = f"{time.time():.6f}"
                logger.info(f"[SILENT MODE] Would have posted to {channel_id}", extra={"ts": mock_ts, "blocks": blocks})

                return {"ok": True, "channel": channel_id, "ts": mock_ts, "message": {"blocks": blocks}}

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
                logger.info(f"[SILENT MODE] Would have posted to {channel_id}", extra={"blocks": blocks})
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
        status: TaskStatus = "in_progress",
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
        self,
        id: str,
        message: str,
        status: TaskStatus = "in_progress",
        output_message: str | None = None,
        replace=False,
    ):
        # Add header
        if self.slack_client is None:
            logger.warning("No Slack client found, skipped update all tasks")
            return

        for slack_message in self.messages:
            channel_id = slack_message["channel"]
            ts = slack_message["ts"]

            if slack_message is None:
                logger.warning("No Slack message, skipping update task")
                continue

            blocks = slack_message.get("message", {}).get("blocks", [])
            plan = next((block for block in blocks if block["type"] == "plan"), None)

            if plan is None:
                continue

            tasks = plan.get("tasks")

            if tasks is None:
                logger.warning("No task found, skipping update task")
                continue

            task = next((task for task in tasks if task["task_id"] == id), None)
            if task is None:
                logger.warning(f"Could not find task with task_id {id}, skipping update task")
                continue

            details = task["details"]
            if replace:
                logger.warning("Replacing Plan Block details")
                details["elements"] = []

            details["elements"].append({"type": "rich_text_section", "elements": [{"type": "text", "text": message}]})

            task["status"] = status
            task["details"] = details

            if output_message:
                output = task["output"]
                output["elements"][0]["elements"][0]["text"] = output_message
                task["output"] = output

            self.update_message(channel_id=channel_id, ts=ts, blocks=blocks)

    def update_task_db(self, created, modified, deleted):
        try:
            for slack_message in self.messages:
                channel_id = slack_message["channel"]
                ts = slack_message["ts"]

                logger.info(
                    "Updating database",
                    extra={
                        "channel_id": channel_id,
                        "ts": ts,
                        "records_created": created,
                        "records_modified": modified,
                        "records_deleted": deleted,
                    },
                )

                # Update data in database
                self.db_handler.update_message(
                    user_id=self.user_id,
                    channel_id=channel_id,
                    ts=ts,
                    created=created,
                    modified=modified,
                    deleted=deleted,
                )
        except Exception as e:
            # Handle unexpected errors
            logger.error(
                "Unexpected error occurred",
                extra={
                    "status_code": 500,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "channel_id": channel_id,
                    "ts": ts,
                    "records_created": created,
                    "records_modified": modified,
                    "records_deleted": deleted,
                },
            )

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

    def create_default_response(self, channel_id, user_id, ts, blocks):
        return {
            "ok": True,
            "channel": channel_id,
            "ts": ts,
            "message": {
                "type": "message",
                "text": "*My knowledge base has been updated!*",
                "user": user_id,
                "ts": ts,
                "blocks": blocks,
            },
        }

    def get_latest_message(self, user_id, channel_id, blocks, s3_event_handler):
        latest_message = self.db_handler.get_sync_state(user_id, channel_id)

        if latest_message is None:
            return None

        last_ts = latest_message.get("last_ts")
        if last_ts:
            time_since_last = time.time() - float(last_ts)
            # Check if message is less than 10 minutes old (600 seconds)
            if time_since_last < 600:
                logger.info(
                    f"Message recently sent to {channel_id} ({int(time_since_last)}s ago). Skipping new message."
                )

                s3_event_handler.created = int(latest_message.get("created", 0))
                s3_event_handler.modified = int(latest_message.get("modified", 0))
                s3_event_handler.deleted = int(latest_message.get("deleted", 0))

                default = self.create_default_response(
                    channel_id=channel_id, user_id=user_id, ts=last_ts, blocks=blocks
                )
                return default
        return None

    def post_initial_message(self, user_id, channel_id, blocks):
        logger.info("Creating new Slack Message")
        response = self.post_message(
            channel_id=channel_id,
            blocks=blocks,
            text_fallback="*My knowledge base has been updated!*",
        )

        if not response or not response.get("ok"):
            logger.error("Error initialising Slack Message.", extra={"response": response})
            return None

        new_ts = response.get("ts")
        if new_ts:
            self.db_handler.save_message(user_id, channel_id, new_ts)

        return response

    def initialise_slack(self):
        # Create new client
        token = get_bot_token()
        slack_client = WebClient(token=token)
        self.slack_client = slack_client

        response = slack_client.auth_test()
        self.user_id = response.get("user_id", "unknown")
        logger.info(f"Authenticated as bot user: {self.user_id}", extra={"response": response})

        # Get Channels where the Bot is a member
        logger.info("Find bot channels...")
        self.target_channels = self.get_bot_channels()

        if not self.target_channels:
            logger.warning("SKIPPING - Bot is not in any channels. No messages sent.")
            return []

        message_default_text = "I am currently syncing changes to my knowledge base.\n This may take a few minutes."

        # Build blocks for Slack message
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": message_default_text,
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
                "elements": [{"type": "plain_text", "text": "Please wait up-to 10 minutes for changes to take effect"}],
            },
        ]

        return blocks

    def initialise_slack_messages(self, s3_event_handler: S3EventHandler):
        """
        Create a new slack message to inform user of SQS event process progress
        or skip if a message was recently created
        """
        try:
            blocks = self.initialise_slack()

            # Broadcast Loop
            logger.info(f"Searching {len(self.target_channels)} channels...")
            responses = []
            for channel_id in self.target_channels:
                try:
                    latest_message = self.get_latest_message(
                        user_id=self.user_id, channel_id=channel_id, s3_event_handler=s3_event_handler, blocks=blocks
                    )
                    if latest_message:
                        responses.append(latest_message)
                        continue

                    new_message = self.post_initial_message(user_id=self.user_id, channel_id=channel_id, blocks=blocks)
                    if new_message:
                        responses.append(new_message)

                except Exception as e:
                    logger.error(
                        f"Failed to initialise slack message for channel: {channel_id}", extra={"exception": e}
                    )

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
                blocks = slack_message.get("message", {}).get("blocks", [])
                plan = next((block for block in blocks if block["type"] == "plan"), None)

                if plan:
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

    def __init__(self):
        self.created = 0
        self.modified = 0
        self.deleted = 0

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

    def process_multiple_s3_events(self, records: list, slack_handler: SlackHandler):
        logger.info("Processing SQS record")

        self.created += len([r for r in records if "ObjectCreated" in r.get("eventName", "")])
        self.modified += len([r for r in records if "ObjectModified" in r.get("eventName", "")])
        self.deleted += len([r for r in records if "ObjectRemoved" in r.get("eventName", "")])

        total = self.created + self.modified + self.deleted

        counts = [
            ("created", self.created),
            ("modified", self.modified),
            ("deleted", self.deleted),
        ]

        # Generate the list only for non-zero values
        message_list = [f"{count} files {action}" for action, count in counts if count > 0]

        if message_list and len(message_list) > 0:
            slack_handler.update_task(
                id=slack_handler.update_block_id, message="Update pending", output_message="Processing...", replace=True
            )
            for i, message in enumerate(message_list):
                output_message = f"Processed a total of {total} record(s)" if (i + 1 == len(message_list)) else None
                slack_handler.update_task(
                    id=slack_handler.update_block_id, message=message, output_message=output_message, replace=(i == 0)
                )
                slack_handler.update_task_db(created=self.created, modified=self.modified, deleted=self.deleted)

    @staticmethod
    def start_ingestion_job():
        try:
            response = bedrock_agent.start_ingestion_job(
                knowledgeBaseId=KNOWLEDGEBASE_ID,
                dataSourceId=DATA_SOURCE_ID,
                description=str(time.time()),
            )

            job_id = response["ingestionJob"]["ingestionJobId"]
            job_status = response["ingestionJob"]["status"]

            logger.info(
                "Successfully started ingestion job",
                extra={"job_id": job_id, "job_status": job_status},
            )
        except Exception as e:
            logger.error(f"Error starting ingestion: {str(e)}")

    def process_multiple_sqs_events(self, slack_handler: SlackHandler, s3_records):
        """Handle multiple individual events from SQS"""
        if s3_records and len(s3_records):
            # Start the ingestion job
            S3EventHandler.start_ingestion_job()
        else:
            logger.info("skipping start_ingestion")

        valid_records = []
        for record in s3_records:
            if record.get("eventSource") != "aws:s3":
                logger.warning(
                    "Skipping non-s3 event",
                    extra={"event_source": record.get("eventSource")},
                )
                continue
            valid_records.append(record)

        # Process event details for the Slack Messages
        if valid_records:
            self.process_multiple_s3_events(records=valid_records, slack_handler=slack_handler)

    def process_batched_queue_events(self, slack_handler: SlackHandler, events: list):
        """Handle collection of batched queue events"""
        for i, event in enumerate(events):
            body = json.loads(event.get("body", "{}"))
            sqs_records = body.get("Records", [])

            if not sqs_records:
                logger.warning("No records in event")
                continue

            logger.info(f"Processing {len(sqs_records)} record(s)")
            output_message = "Search Complete" if (i + 1 == len(events)) else None
            slack_handler.update_task(
                id=slack_handler.fetching_block_id,
                message=f"Found {len(sqs_records)} events",
                output_message=output_message,
                replace=True,
            )

            self.process_multiple_sqs_events(slack_handler, sqs_records)

        logger.info(f"Completed {len(sqs_records)} event(s)")

    @staticmethod
    def close_sqs_events(events):
        logger.info(f"Closing {len(events)} sqs events")
        for event in events:
            receipt_handle = event.get("receiptHandle") or event.get("ReceiptHandle")

            if not receipt_handle:
                logger.warning("No receipt handle found in event, skipping deletion.")
                continue

            try:
                sqs.delete_message(QueueUrl=SQS_URL, ReceiptHandle=receipt_handle)
                logger.info("Successfully deleted sqs message from queue")
            except Exception as e:
                logger.error("Failed to delete sqs message from queue", extra={"Exception": e})

    @staticmethod
    def search_sqs_for_events():
        logger.info("Searching for new events")
        response = sqs.receive_message(QueueUrl=SQS_URL, MaxNumberOfMessages=10, WaitTimeSeconds=20)

        events = []
        messages = response.get("Messages", [])
        if not messages:
            logger.warning("No messages found", extra={"response": response, "messages": messages})
            return events

        logger.info(f"Found {len(messages)} messages in SQS", extra={"response": response, "messages": messages})
        for message in messages:
            body = message.get("Body", "{}")
            message_events = json.loads(body)
            if message_events:
                events.append({"body": message.get("Body", "{}"), "receiptHandle": message.get("ReceiptHandle")})

        logger.info(f"Found {len(messages)} total event(s) in SQS messages")
        return events


def search_and_process_sqs_events(event):
    """
    Check if there are waiting SQS events.
    While SQS keep appearing, keep looking - limit to 20 iterations.
    """
    events = event.get("Records", [])
    loop_count = 20

    s3_event_handler = S3EventHandler()

    is_silent = not get_bot_active()  # Mute Slack for PRs
    slack_handler = SlackHandler(silent=is_silent)
    slack_handler.initialise_slack_messages(s3_event_handler=s3_event_handler)

    for i in range(loop_count):
        logger.info(f"Starting process round {i + 1}")

        # If we don't have events in hand, search the queue
        if not events:
            break

        # If we have events (either from the initial seed or the search above), process them
        if events and len(events) > 0:
            logger.info("Found events, process")
            s3_event_handler.process_batched_queue_events(slack_handler, events)
            if i > 0:  # Only close if fetched, not received
                s3_event_handler.close_sqs_events(events)

        # Clear the list so the NEXT loop iteration knows to search again
        logger.info("Search for any prompts left in the queue")
        events = s3_event_handler.search_sqs_for_events()

    slack_handler.complete_plan()


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event, context):
    """
    Main Lambda handler for a queue-service (S3-triggered) knowledge base synchronization
    """
    start_time = time.time()

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
