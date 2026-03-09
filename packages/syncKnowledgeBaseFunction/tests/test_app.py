import json
import uuid
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock, DEFAULT
from botocore.exceptions import ClientError

TEST_BOT_TOKEN = "test-bot-token"


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    env_vars = {
        "KNOWLEDGEBASE_ID": "test-kb-id",
        "DATA_SOURCE_ID": "test-ds-id",
        "AWS_REGION": "eu-west-2",
        "SQS_URL": "example",
    }
    with patch.dict(os.environ, env_vars):
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
def receive_multiple_s3_event():
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
def fetch_multiple_sqs_event(receive_multiple_s3_event):
    """Mock incoming SQS event structure as expected by the new logic"""
    return {
        "Messages": [
            {
                "MessageId": str(uuid.uuid4()),
                "Body": json.dumps(receive_multiple_s3_event),
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


@patch("app.handler.Slack_Handler.initialise_slack_messages")
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
        description="Sync: test-bucket",
    )


@patch("app.handler.Slack_Handler.initialise_slack_messages")
@patch("boto3.client")
@patch("time.time")
def test_handler_multiple_files(
    mock_time,
    mock_boto_client,
    mock_initialise_slack_messages,
    mock_env,
    mock_get_bot_token,
    lambda_context,
    receive_multiple_s3_event,
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

    result = handler(receive_multiple_s3_event, lambda_context)

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
    receive_multiple_s3_event,
    fetch_sqs_event,
):
    """Test handler with multiple S3 records"""
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]

    mock_bedrock = MagicMock()
    mock_sqs = MagicMock()

    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }
    mock_sqs.receive_message.side_effect = [fetch_sqs_event, {}]

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

    with patch.object(app.handler.Slack_Handler, "initialise_slack_messages", return_value=(DEFAULT, [])):
        result = app.handler.handler(receive_multiple_s3_event, lambda_context)

        assert result["statusCode"] == 200
        assert "Successfully polled and processed sqs events" in result["body"]
        assert mock_bedrock.start_ingestion_job.call_count == 3  # Initial 2 + 1


@patch("boto3.client")
@patch("time.time")
def test_handler_fetch_multiple_files(
    mock_time,
    mock_boto_client,
    mock_env,
    mock_get_bot_token,
    lambda_context,
    receive_multiple_s3_event,
    fetch_multiple_sqs_event,
):
    """Test handler with multiple S3 records"""
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]

    mock_bedrock = MagicMock()
    mock_sqs = MagicMock()

    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }
    mock_sqs.receive_message.side_effect = [fetch_multiple_sqs_event, {}]

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

    with patch.object(app.handler.Slack_Handler, "initialise_slack_messages", return_value=(DEFAULT, [])):
        result = app.handler.handler(receive_multiple_s3_event, lambda_context)

        assert result["statusCode"] == 200
        assert "Successfully polled and processed sqs events" in result["body"]
        assert mock_bedrock.start_ingestion_job.call_count == 4  # Initial 2 + 2


@patch("boto3.client")
@patch("time.time")
def test_handler_fetch_multiple_files_handle_infinity(
    mock_time,
    mock_boto_client,
    mock_env,
    mock_get_bot_token,
    lambda_context,
    receive_multiple_s3_event,
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

    with patch.object(app.handler.Slack_Handler, "initialise_slack_messages", return_value=(DEFAULT, [])):
        result = app.handler.handler(receive_multiple_s3_event, lambda_context)

        assert result["statusCode"] == 200
        assert "Successfully polled and processed sqs events" in result["body"]
        assert mock_bedrock.start_ingestion_job.call_count == 21  # Once for original message + max (20)


@patch("boto3.client")
@patch("time.time")
def test_handler_conflict_exception(
    mock_time,
    mock_boto_client,
    mock_env,
    lambda_context,
    receive_s3_event,
    mock_get_bot_token,
):
    """Test handler with ConflictException (job already running)"""
    mock_time.side_effect = [1000, 1001, 1002, 1003]

    error = ClientError(
        error_response={"Error": {"Code": "ConflictException", "Message": "Job already running"}},
        operation_name="StartIngestionJob",
    )
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.side_effect = error

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    import app.handler

    with patch.object(app.handler.Slack_Handler, "initialise_slack_messages", return_value=(DEFAULT, [])), patch.object(
        app.handler.S3_Event_Handler, "handle_client_error"
    ) as mock_handle_client_error:

        result = app.handler.handler(receive_s3_event, lambda_context)

        assert result["statusCode"] == 200
        assert "Successfully polled and processed sqs events" in result["body"]
        assert mock_handle_client_error.call_count == 1


@patch("boto3.client")
@patch("time.time")
def test_handler_aws_error(mock_time, mock_boto_client, mock_env, lambda_context, receive_s3_event):
    """Test handler with other AWS error"""
    mock_time.side_effect = [1000, 1001, 1002, 1003]
    error = ClientError(
        error_response={"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        operation_name="StartIngestionJob",
    )
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.side_effect = error

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    import app.handler

    with patch.object(app.handler.Slack_Handler, "initialise_slack_messages", return_value=(DEFAULT, [])), patch.object(
        app.handler.S3_Event_Handler, "handle_client_error"
    ) as mock_handle_client_error:

        result = app.handler.handler(receive_s3_event, lambda_context)

        assert result["statusCode"] == 200
        assert "Successfully polled and processed sqs events" in result["body"]
        assert mock_handle_client_error.call_count == 1


@patch("boto3.client")
@patch("time.time")
def test_handler_unexpected_error(mock_time, mock_boto_client, mock_env, lambda_context, receive_s3_event):
    """Test handler with unexpected error"""
    mock_time.side_effect = [1000, 1001, 1002, 1003]
    mock_bedrock = mock_boto_client.return_value
    mock_bedrock.start_ingestion_job.side_effect = Exception("Unexpected error")

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    import app.handler

    with patch.object(app.handler.Slack_Handler, "initialise_slack_messages", return_value=(DEFAULT, [])), patch.object(
        app.handler.S3_Event_Handler, "handle_client_error"
    ) as mock_handle_client_error:

        result = app.handler.handler(receive_s3_event, lambda_context)

        assert result["statusCode"] == 200
        assert "Successfully polled and processed sqs events" in result["body"]
        assert mock_handle_client_error.call_count == 1


@patch("app.handler.KNOWLEDGEBASE_ID", "")
@patch("app.handler.DATA_SOURCE_ID", "")
def test_handler_missing_env_vars(lambda_context, receive_s3_event):
    """Test handler with missing environment variables"""
    from app.handler import handler

    result = handler(receive_s3_event, lambda_context)

    assert result["statusCode"] == 500
    assert "Configuration error" in result["body"]


@patch("app.handler.Slack_Handler.initialise_slack_messages")
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


@patch("app.handler.Slack_Handler.initialise_slack_messages")
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


@patch("app.handler.Slack_Handler.initialise_slack_messages")
@patch("boto3.client")
def test_handler_empty_records(mock_boto_client, mock_initialise_slack_messages, mock_env, lambda_context):
    """Test handler with empty records"""
    empty_event = {"Records": []}
    mock_initialise_slack_messages.return_value = (DEFAULT, [])

    from app.handler import handler

    result = handler(empty_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully polled and processed sqs events" in result["body"]


@patch("app.handler.Slack_Handler.initialise_slack_messages")
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
    from app.handler import S3_Event_Handler

    assert S3_Event_Handler.is_supported_file_type(filename) is expected


@patch("app.handler.Slack_Handler.initialise_slack_messages")
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


@patch("app.handler.Slack_Handler.initialise_slack_messages")
@patch("boto3.client")
@patch("slack_sdk.WebClient")
@patch("time.time")
def test_slack_handler_success(
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


@patch("app.handler.Slack_Handler.initialise_slack_messages")
@patch("boto3.client")
@patch("slack_sdk.WebClient")
@patch("time.time")
def test_slack_handler_success_multiple(
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


@patch("app.handler.Slack_Handler.initialise_slack_messages")
@patch("boto3.client")
@patch("slack_sdk.WebClient")
@patch("time.time")
def test_slack_handler_client_failure(
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
