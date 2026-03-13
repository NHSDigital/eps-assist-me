import copy
import json
import uuid
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock, DEFAULT, call


TEST_BOT_TOKEN = "test-bot-token"


@pytest.fixture(autouse=True)
def mock_env():
    env_vars = {
        "KNOWLEDGEBASE_ID": "test-kb-id",
        "DATA_SOURCE_ID": "test-ds-id",
        "AWS_REGION": "eu-west-2",
        "SQS_URL": "example",
        "SLACK_BOT_ACTIVE": "true",
    }

    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.function_name = "test-function"
    context.aws_request_id = "test-request-id"
    return context


@pytest.fixture
def mock_get_parameter():
    def fake_get_parameter(name: str, *args, **kwargs):
        return {
            "/test/bot-token": json.dumps({"token": "test-token"}),
            "/test/signing-secret": json.dumps({"secret": "test-secret"}),
        }[name]

    with patch("app.core.config.get_parameter", side_effect=fake_get_parameter) as mock:
        yield mock


@pytest.fixture
def mock_get_bot_token():
    with patch("app.config.config.get_bot_token") as mock_get_bot_token:
        mock_instance = MagicMock()
        mock_get_bot_token.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def receive_s3_event():
    """Mock S3 event"""
    return {
        "Records": [
            {
                "eventSource": "aws:sqs",
                "body": json.dumps(
                    {
                        "Records": [
                            {
                                "eventSource": "aws:s3",
                                "eventName": "ObjectCreated:Put",
                                "s3": {
                                    "bucket": {"name": "test-bucket"},
                                    "object": {"key": "test-file.pdf", "size": 1024},
                                },
                            }
                        ]
                    }
                ),
            }
        ]
    }


@pytest.fixture
def receive_multiple_s3_events():
    """Mock S3 event with multiple records"""
    return {
        "Records": [
            {
                "eventSource": "aws:sqs",
                "body": json.dumps(
                    {
                        "Records": [
                            {
                                "eventSource": "aws:s3",
                                "eventName": "ObjectCreated:Put",
                                "s3": {
                                    "bucket": {"name": "test-bucket"},
                                    "object": {"key": "file1.pdf", "size": 1024},
                                },
                            },
                            {
                                "eventSource": "aws:s3",
                                "eventName": "ObjectRemoved:Delete",
                                "s3": {
                                    "bucket": {"name": "test-bucket"},
                                    "object": {"key": "file2.pdf", "size": 2048},
                                },
                            },
                        ]
                    }
                ),
            }
        ]
    }


@pytest.fixture
def fetch_sqs_event(receive_s3_event):
    """Mock incoming SQS event structure as expected by the new logic"""
    return {"Messages": [{"MessageId": str(uuid.uuid4()), "Body": json.dumps(receive_s3_event)}]}


@pytest.fixture
def fetch_multiple_sqs_event(receive_multiple_s3_events):
    """Mock incoming SQS event structure as expected by the new logic"""
    return {
        "Messages": [
            {
                "MessageId": str(uuid.uuid4()),
                "Body": json.dumps(receive_multiple_s3_events),
            }
        ]
    }


@pytest.fixture
def slack_message_event():
    return {
        "channel": "test",
        "ts": "123456",
        "message": {
            "blocks": [
                {
                    "type": "plan",
                    "title": "Thinking completed",
                    "tasks": [
                        {
                            "task_id": "call_001",
                            "title": "Fetched user profile information",
                            "status": "in_progress",
                            "details": {
                                "type": "rich_text",
                                "block_id": "viMWO",
                                "elements": [
                                    {
                                        "type": "rich_text_section",
                                        "elements": [{"type": "text", "text": "Searched database..."}],
                                    }
                                ],
                            },
                            "output": {
                                "type": "rich_text",
                                "block_id": "viMWO",
                                "elements": [
                                    {
                                        "type": "rich_text_section",
                                        "elements": [{"type": "text", "text": "Profile data loaded"}],
                                    }
                                ],
                            },
                        },
                        {
                            "task_id": "call_002",
                            "title": "Checked user permissions",
                            "status": "pending",
                        },
                        {
                            "task_id": "call_003",
                            "title": "Generated comprehensive user report",
                            "status": "complete",
                            "output": {
                                "type": "rich_text",
                                "block_id": "crsk",
                                "elements": [
                                    {
                                        "type": "rich_text_section",
                                        "elements": [{"type": "text", "text": "15 data points compiled"}],
                                    }
                                ],
                            },
                        },
                    ],
                }
            ],
        },
    }


@patch("app.handler.SlackHandler.initialise_slack_messages")
@patch("boto3.client")
@patch("time.time")
def test_handler_success(
    mock_time, mock_boto_client, mock_initialise_slack_messages, mock_env, lambda_context, receive_s3_event
):
    """Test successful handler execution"""
    mock_time.side_effect = [1000, 1001, 1002, 1003]
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }
    mock_initialise_slack_messages.return_value = (DEFAULT, [])

    from app.handler import handler

    result = handler(receive_s3_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]
    mock_boto_client.assert_any_call("bedrock-agent")
    mock_boto_client.assert_any_call("sqs")
    mock_bedrock.start_ingestion_job.assert_called_once_with(
        knowledgeBaseId="test-kb-id",
        dataSourceId="test-ds-id",
        description="1001",
    )


@patch("app.handler.SlackHandler.initialise_slack_messages")
@patch("boto3.client")
@patch("time.time")
def test_handler_multiple_files(
    mock_time,
    mock_boto_client,
    mock_initialise_slack_messages,
    mock_env,
    mock_get_bot_token,
    lambda_context,
    receive_multiple_s3_events,
):
    """Test handler with multiple S3 records"""
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }
    mock_initialise_slack_messages.return_value = (DEFAULT, [])

    # Force reload the module to catch the new patches
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    result = handler(receive_multiple_s3_events, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]
    assert mock_bedrock.start_ingestion_job.call_count == 2


@patch("boto3.client")
@patch("time.time")
def test_handler_fetch_files(
    mock_time,
    mock_boto_client,
    mock_env,
    mock_get_bot_token,
    lambda_context,
    receive_multiple_s3_events,
    fetch_sqs_event,
):
    """Test handler with multiple S3 records"""
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]

    mock_bedrock = MagicMock()
    mock_sqs = MagicMock()

    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }
    mock_sqs.receive_message.side_effect = [fetch_sqs_event] + [{}] * 21

    def boto_client_router(service_name, **kwargs):
        if service_name == "bedrock-agent":
            return mock_bedrock
        elif service_name == "sqs":
            return mock_sqs
        return MagicMock()

    mock_boto_client.side_effect = boto_client_router

    # Force reload the module to catch the new patches
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    import app.handler

    with patch.object(app.handler.SlackHandler, "initialise_slack_messages", return_value=(DEFAULT, [])):
        result = app.handler.handler(receive_multiple_s3_events, lambda_context)

        assert result["statusCode"] == 200
        assert "Successfully polled and processed sqs events" in result["body"]
        assert mock_bedrock.start_ingestion_job.call_count == 2


@patch("boto3.client")
@patch("time.time")
def test_handler_fetch_multiple_files(
    mock_time,
    mock_boto_client,
    mock_env,
    mock_get_bot_token,
    lambda_context,
    receive_multiple_s3_events,
    fetch_multiple_sqs_event,
):
    """Test handler with multiple S3 records"""
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]

    mock_bedrock = MagicMock()
    mock_sqs = MagicMock()

    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }
    # mock_sqs.receive_message.side_effect = [fetch_multiple_sqs_event] + [[]] * 29
    mock_sqs.receive_message.side_effect = [fetch_multiple_sqs_event] + [{}] * 21

    def boto_client_router(service_name, **kwargs):
        if service_name == "bedrock-agent":
            return mock_bedrock
        elif service_name == "sqs":
            return mock_sqs
        return MagicMock()

    mock_boto_client.side_effect = boto_client_router

    # Force reload the module to catch the new patches
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    import app.handler

    with patch.object(app.handler.SlackHandler, "initialise_slack_messages", return_value=(DEFAULT, [])):
        result = app.handler.handler(receive_multiple_s3_events, lambda_context)

        assert result["statusCode"] == 200
        assert "Successfully polled and processed sqs events" in result["body"]
        assert mock_bedrock.start_ingestion_job.call_count == 2


@patch("boto3.client")
@patch("time.time")
def test_handler_fetch_multiple_files_handle_infinity(
    mock_time,
    mock_boto_client,
    mock_env,
    mock_get_bot_token,
    lambda_context,
    receive_multiple_s3_events,
    fetch_sqs_event,
):
    """Test handler with multiple S3 records"""
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]

    mock_bedrock = MagicMock()
    mock_sqs = MagicMock()

    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }
    mock_sqs.receive_message.return_value = fetch_sqs_event

    def boto_client_router(service_name, **kwargs):
        if service_name == "bedrock-agent":
            return mock_bedrock
        elif service_name == "sqs":
            return mock_sqs
        return MagicMock()

    mock_boto_client.side_effect = boto_client_router

    # Force reload the module to catch the new patches
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    import app.handler

    with patch.object(app.handler.SlackHandler, "initialise_slack_messages", return_value=(DEFAULT, [])):
        result = app.handler.handler(receive_multiple_s3_events, lambda_context)

        assert result["statusCode"] == 200
        assert "Successfully polled and processed sqs events" in result["body"]
        assert mock_bedrock.start_ingestion_job.call_count == 2  # Once for original message + max (20)


@patch("slack_sdk.WebClient")
@patch("app.config.config.get_bot_token")
@patch("boto3.client")
@patch("time.time")
def test_handler_slack_success(
    mock_time,
    mock_boto_client,
    mock_get_bot_token,
    mock_webclient_class,
    mock_env,
    lambda_context,
    receive_s3_event,
):
    """Test successful handler execution with actual Slack WebClient interaction"""
    # Mock timing
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]

    # Setup Boto3 Mock
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    # Setup Slack SDK WebClient Mock
    mock_slack_client = MagicMock()
    mock_webclient_class.return_value = mock_slack_client
    mock_get_bot_token.return_value = "test-bot-token"

    # Mock the initial auth and channel fetching
    mock_slack_client.auth_test.return_value = {"user_id": "U123456"}

    # Needs to be a list because the handler uses: `for result in self.slack_client.conversations_list(...)`
    mock_slack_client.conversations_list.return_value = [{"channels": [{"id": "C123456"}]}]

    # Echo the blocks back to mimic Slack's actual API response behavior.
    def mock_post_message_side_effect(**kwargs):
        return {
            "ok": True,
            "channel": kwargs.get("channel"),
            "ts": "1002",
            "message": {"blocks": kwargs.get("blocks", [])},
        }

    mock_slack_client.chat_postMessage.side_effect = mock_post_message_side_effect
    mock_slack_client.chat_update.return_value = {"ok": True}

    # Force module reload to apply new patches from the source modules
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Run the handler
    result = handler(receive_s3_event, lambda_context)

    # --- Assertions ---
    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]

    # Assert Boto3 was triggered correctly
    mock_bedrock.start_ingestion_job.assert_called_once_with(
        knowledgeBaseId="test-kb-id",
        dataSourceId="test-ds-id",
        description="1002",
    )

    # Assert Slack WebClient setup calls
    mock_slack_client.auth_test.assert_called_once()
    mock_slack_client.conversations_list.assert_called_once_with(types=["private_channel"], limit=1000)

    # Assert Messages were posted and updated
    mock_slack_client.chat_postMessage.assert_called_once()
    assert mock_slack_client.chat_update.call_count == 3  # Update details, update tasks, close


@patch("app.config.config.get_bot_active")
@patch("slack_sdk.WebClient")
@patch("app.config.config.get_bot_token")
@patch("boto3.client")
@patch("time.time")
def test_handler_slack_silent_success(
    mock_time,
    mock_boto_client,
    mock_get_bot_token,
    mock_webclient_class,
    mock_get_bot_active,
    mock_env,
    lambda_context,
    receive_s3_event,
):
    """Test successful handler execution with actual Slack WebClient interaction"""
    # Mock timing
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]

    # Setup Boto3 Mock
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    # Setup Slack SDK WebClient Mock
    mock_slack_client = MagicMock()
    mock_webclient_class.return_value = mock_slack_client
    mock_get_bot_token.return_value = "test-bot-token"
    mock_get_bot_active.return_value = False

    # Mock the initial auth and channel fetching
    mock_slack_client.auth_test.return_value = {"user_id": "U123456"}

    # Needs to be a list because the handler uses: `for result in self.slack_client.conversations_list(...)`
    mock_slack_client.conversations_list.return_value = [{"channels": [{"id": "123456"}]}]

    # Force module reload to apply new patches from the source modules
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Run the handler
    result = handler(receive_s3_event, lambda_context)

    # --- Assertions ---
    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]

    # Assert Boto3 was triggered correctly
    mock_bedrock.start_ingestion_job.assert_called_once_with(
        knowledgeBaseId="test-kb-id",
        dataSourceId="test-ds-id",
        description="1002",
    )

    # Assert Slack WebClient setup calls
    mock_slack_client.auth_test.assert_called_once()
    mock_slack_client.conversations_list.assert_called_once_with(types=["private_channel"], limit=1000)

    # Assert Messages were posted and updated
    mock_slack_client.chat_postMessage.assert_not_called()
    mock_slack_client.chat_update.asset_not_called()


@patch("app.handler.KNOWLEDGEBASE_ID", "")
@patch("app.handler.DATA_SOURCE_ID", "")
@patch("boto3.client")
def test_handler_missing_env_vars(mock_boto, lambda_context, receive_s3_event):
    """Test handler with missing environment variables"""
    from app.handler import handler

    result = handler(receive_s3_event, lambda_context)

    assert result["statusCode"] == 500
    assert "Configuration error" in result["body"]


@patch("app.handler.SlackHandler.initialise_slack_messages")
@patch("boto3.client")
def test_handler_invalid_s3_record(mock_boto_client, mock_initialise_slack_messages, mock_env, lambda_context):
    """Test handler with invalid S3 record"""
    invalid_event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {},  # Missing name
                    "object": {},  # Missing key
                },
            }
        ]
    }
    mock_initialise_slack_messages.return_value = (DEFAULT, [])

    from app.handler import handler

    result = handler(invalid_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]


@patch("app.handler.SlackHandler.initialise_slack_messages")
@patch("boto3.client")
def test_handler_non_s3_event(mock_boto_client, mock_initialise_slack_messages, mock_env, lambda_context):
    """Test handler with non-S3 event"""
    non_s3_event = {
        "Records": [
            {
                "eventSource": "aws:sns",
                "eventName": "Notification",
            }
        ]
    }
    mock_initialise_slack_messages.return_value = (DEFAULT, [])

    from app.handler import handler

    result = handler(non_s3_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]


@patch("app.handler.SlackHandler.initialise_slack_messages")
@patch("boto3.client")
def test_handler_empty_records(mock_boto_client, mock_initialise_slack_messages, mock_env, lambda_context):
    """Test handler with empty records"""
    empty_event = {"Records": []}
    mock_initialise_slack_messages.return_value = (DEFAULT, [])

    from app.handler import handler

    result = handler(empty_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]


@patch("app.handler.SlackHandler.initialise_slack_messages")
@patch("boto3.client")
@pytest.mark.parametrize(
    "filename,expected",
    [
        # Supported types
        ("document.pdf", True),
        ("readme.txt", True),
        ("notes.md", True),
        ("data.csv", True),
        ("report.docx", True),
        ("spreadsheet.xlsx", True),
        ("page.html", True),
        ("config.json", True),
        # Case insensitive
        ("DOCUMENT.PDF", True),
        ("File.TXT", True),
        # Unsupported types
        ("image.jpg", False),
        ("video.mp4", False),
        ("archive.zip", False),
        ("executable.exe", False),
        ("no_extension", False),
    ],
)
def test_is_supported_file_type(mock_boto_client, mock_initialise_slack_messages, filename, expected):
    """Test file type allowlist validation"""
    from app.handler import S3EventHandler

    assert S3EventHandler.is_supported_file_type(filename) is expected


@patch("app.handler.SlackHandler.initialise_slack_messages")
@patch("boto3.client")
def test_handler_unsupported_file_type(mock_boto_client, mock_initialise_slack_messages, mock_env, lambda_context):
    """Test handler skips unsupported file types"""
    unsupported_event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "image.jpg", "size": 1024},
                },
            }
        ]
    }
    mock_initialise_slack_messages.return_value = (DEFAULT, [])

    from app.handler import handler

    result = handler(unsupported_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]


@patch("app.handler.SlackHandler.initialise_slack_messages")
@patch("boto3.client")
@patch("slack_sdk.WebClient")
@patch("time.time")
def test_SlackHandler_success(
    mock_time,
    mock_slack_client,
    mock_boto_client,
    mock_initialise_slack_messages,
    mock_env,
    lambda_context,
    receive_s3_event,
    slack_message_event,
):
    """Test successful handler execution"""
    mock_time.side_effect = [1000, 1001, 1002, 1003]

    # Slack
    mock_instance = mock_slack_client.return_value
    mock_instance.chat_update.return_value = {"ok": True}
    mock_initialise_slack_messages.return_value = (mock_instance, [slack_message_event])

    # Boto
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    result = handler(receive_s3_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]
    mock_instance.chat_update.call_count = 2


@patch("app.handler.SlackHandler.initialise_slack_messages")
@patch("boto3.client")
@patch("slack_sdk.WebClient")
@patch("time.time")
def test_SlackHandler_success_multiple(
    mock_time,
    mock_slack_client,
    mock_boto_client,
    mock_initialise_slack_messages,
    mock_env,
    lambda_context,
    receive_s3_event,
    slack_message_event,
):
    """
    Test successful execution of slack messages.
    Should not be any different then a single message
    """
    mock_time.side_effect = [1000, 1001, 1002, 1003]

    # Slack
    mock_instance = mock_slack_client.return_value
    mock_instance.chat_update.return_value = {"ok": True}
    mock_initialise_slack_messages.return_value = (
        mock_instance,
        [slack_message_event, slack_message_event, slack_message_event],
    )

    # Boto
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    result = handler(receive_s3_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]
    mock_instance.chat_update.call_count = 2


@patch("app.handler.SlackHandler.initialise_slack_messages")
@patch("boto3.client")
@patch("slack_sdk.WebClient")
@patch("time.time")
def test_SlackHandler_client_failure(
    mock_time,
    mock_slack_client,
    mock_boto_client,
    mock_initialise_slack_messages,
    mock_env,
    lambda_context,
    receive_s3_event,
    slack_message_event,
):
    """
    Test successful execution of slack messages.
    If a post fails to send, it shouldn't stop the rest of the items in the queue
    """
    mock_time.side_effect = [1000, 1001, 1002, 1003]

    # Slack
    mock_instance = mock_slack_client.return_value
    mock_instance.chat_update.return_value = {"ok": False}
    mock_initialise_slack_messages.return_value = (
        mock_instance,
        [slack_message_event, slack_message_event, slack_message_event],
    )

    # Boto
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    result = handler(receive_s3_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]
    mock_instance.chat_update.call_count = 2


@patch("slack_sdk.WebClient")
@patch("app.config.config.get_bot_token")
@patch("boto3.client")
@patch("time.time")
def test_process_s3_event_formatting(
    mock_time,
    mock_boto_client,
    mock_get_bot_token,
    mock_webclient_class,
    mock_env,
    lambda_context,
    receive_s3_event,
):
    """Test successful handler execution with actual Slack WebClient interaction"""
    # Mock timing
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]

    # Setup Boto3 Mock
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    # Setup Slack SDK WebClient Mock
    mock_slack_client = MagicMock()
    mock_webclient_class.return_value = mock_slack_client
    mock_get_bot_token.return_value = "test-bot-token"

    # Mock the initial auth and channel fetching
    mock_slack_client.auth_test.return_value = {"user_id": "U123456"}

    # Needs to be a list because the handler uses: `for result in self.slack_client.conversations_list(...)`
    mock_slack_client.conversations_list.return_value = [{"channels": [{"id": "C123456"}]}]

    # Echo the blocks back to mimic Slack's actual API response behavior.
    def mock_post_message_side_effect(**kwargs):
        return {
            "ok": True,
            "channel": kwargs.get("channel"),
            "ts": "1002",
            "message": {"blocks": kwargs.get("blocks", [])},
        }

    mock_slack_client.chat_postMessage.side_effect = mock_post_message_side_effect
    mock_slack_client.chat_update.return_value = {"ok": True}

    # Force module reload to apply new patches from the source modules
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Run the handler
    result = handler(receive_s3_event, lambda_context)

    # --- Assertions ---
    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]

    # Assert Boto3 was triggered correctly
    mock_bedrock.start_ingestion_job.assert_called_once_with(
        knowledgeBaseId="test-kb-id",
        dataSourceId="test-ds-id",
        description="1002",
    )

    # Assert Slack WebClient setup calls
    calls = mock_slack_client.chat_update.call_args_list
    assert len(calls) > 0, "Expected chat_update to be called."

    # Verify the formatted message made its way into the blocks sent to chat_update
    last_call_blocks_str = str(calls[-1].kwargs.get("blocks", []))
    assert "1 files created" in last_call_blocks_str


@patch("slack_sdk.WebClient")
@patch("app.config.config.get_bot_token")
@patch("boto3.client")
@patch("time.time")
def test_process_multiple_s3_events_formatting(
    mock_time,
    mock_boto_client,
    mock_get_bot_token,
    mock_webclient_class,
    mock_env,
    lambda_context,
    receive_multiple_s3_events,
):
    """Test successful handler execution with actual Slack WebClient interaction"""
    # Mock timing
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]

    # Setup Boto3 Mock
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    # Setup Slack SDK WebClient Mock
    mock_slack_client = MagicMock()
    mock_webclient_class.return_value = mock_slack_client
    mock_get_bot_token.return_value = "test-bot-token"

    # Mock the initial auth and channel fetching
    mock_slack_client.auth_test.return_value = {"user_id": "U123456"}

    # Needs to be a list because the handler uses: `for result in self.slack_client.conversations_list(...)`
    mock_slack_client.conversations_list.return_value = [{"channels": [{"id": "C123456"}]}]

    # Echo the blocks back to mimic Slack's actual API response behavior.
    def mock_post_message_side_effect(**kwargs):
        return {
            "ok": True,
            "channel": kwargs.get("channel"),
            "ts": "1002",
            "message": {"blocks": kwargs.get("blocks", [])},
        }

    mock_slack_client.chat_postMessage.side_effect = mock_post_message_side_effect
    mock_slack_client.chat_update.return_value = {"ok": True}

    # Force module reload to apply new patches from the source modules
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Run the handler
    result = handler(receive_multiple_s3_events, lambda_context)

    # --- Assertions ---
    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]

    # Assert Boto3 was triggered correctly
    mock_bedrock.start_ingestion_job.assert_has_calls(
        [
            call(knowledgeBaseId="test-kb-id", dataSourceId="test-ds-id", description="1002"),
            call(knowledgeBaseId="test-kb-id", dataSourceId="test-ds-id", description="1003"),
        ]
    )

    # Assert Slack WebClient setup calls
    calls = mock_slack_client.chat_update.call_args_list
    assert len(calls) > 0, "Expected chat_update to be called."

    # Verify the formatted message made its way into the blocks sent to chat_update
    last_call_blocks_str = str(calls[-1].kwargs.get("blocks", []))
    assert "1 files created" in last_call_blocks_str
    assert "1 files deleted" in last_call_blocks_str


@patch("boto3.client")
def test_slack_handler_create_task_structure(mock_boto):
    """Test create_task generates the exact nested dictionary structure required by Slack Block Kit"""
    from app.handler import SlackHandler

    handler = SlackHandler()
    plan_block = {"title": "Original Title", "tasks": []}

    # Generate a task and append it to the plan
    task = handler.create_task(
        id="test_task_123",
        title="Syncing Documents",
        plan=plan_block,
        details=["Found 5 files"],
        outputs=["All files synced"],
        status="in_progress",
    )

    # 1. Verify the standalone task dictionary structure
    assert task["task_id"] == "test_task_123"
    assert task["title"] == "Syncing Documents"
    assert task["status"] == "in_progress"

    # 2. Verify the rich_text generation for details and outputs
    assert len(task["details"]["elements"]) == 1
    assert task["details"]["elements"][0]["elements"][0]["text"] == "Found 5 files"
    assert len(task["output"]["elements"]) == 1

    # 3. Verify the side-effects on the passed `plan` dictionary
    assert len(plan_block["tasks"]) == 1
    assert plan_block["title"] == "Syncing Documents..."  # Method explicitly alters the plan title


@patch("boto3.client")
def test_slack_handler_complete_plan(mock_boto_client, slack_message_event, mock_env):
    """Test complete_plan correctly mutates the message state and pushes updates"""
    from app.handler import SlackHandler

    handler = SlackHandler(False)
    handler.slack_client = MagicMock()

    # Deep copy the fixture so we don't mutate the global test state
    mock_message = copy.deepcopy(slack_message_event)
    handler.messages = [mock_message]

    # Execute
    handler.complete_plan()

    # Verify the in-memory state was mutated correctly
    plan_block = handler.messages[0]["message"]["blocks"][0]
    assert plan_block["title"] == "Processing complete!"

    # Verify EVERY task within the plan was updated to "complete"
    for task in plan_block["tasks"]:
        assert task["status"] == "complete"

    # Verify the API call was made to push the mutated state
    handler.slack_client.chat_update.assert_called_once_with(
        channel="test", ts="123456", blocks=handler.messages[0]["message"]["blocks"], text="Updating Source Files"
    )


@patch("boto3.client")
def test_validate_s3_event_missing_keys(mock_boto):
    """Test validation logic gracefully rejects payloads missing necessary S3 identifiers without throwing KeyError"""
    from app.handler import S3EventHandler

    # Missing bucket
    assert S3EventHandler.validate_s3_event(None, "doc.pdf") is False
    assert S3EventHandler.validate_s3_event("", "doc.pdf") is False

    # Missing key
    assert S3EventHandler.validate_s3_event("my-bucket", None) is False
    assert S3EventHandler.validate_s3_event("my-bucket", "") is False

    # Valid
    assert S3EventHandler.validate_s3_event("my-bucket", "doc.pdf") is True


@patch("app.handler.S3EventHandler.search_sqs_for_events")
@patch("app.handler.S3EventHandler.process_batched_queue_events")
@patch("app.handler.S3EventHandler.close_sqs_events")
@patch("app.handler.SlackHandler.initialise_slack_messages")
@patch("boto3.client")
def test_search_and_process_sqs_events(mock_boto, mock_slack_init, mock_close, mock_process, mock_search):
    """Test the while-loop equivalent exits early when the queue is empty, rather than looping 20 times"""
    from app.handler import search_and_process_sqs_events

    initial_event = {"Records": ["Initial Event"]}

    # Simulate finding 1 new event on the first search, then 0 on the second search
    mock_search.side_effect = [[{"Records": ["Polled Event 1"]}]] + [
        []
    ] * 21  # Empty list triggers the `if not events: break`

    search_and_process_sqs_events(initial_event)

    # Iteration 0: Processes initial event, searches SQS (finds 1)
    # Iteration 1: Closes initial event, processes new event, searches SQS (finds 0)
    # Iteration 2: Loop breaks immediately.

    assert mock_process.call_count == 2
    assert mock_close.call_count == 2
    assert mock_search.call_count == 2
