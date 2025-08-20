import pytest
import os
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    env_vars = {"KNOWLEDGEBASE_ID": "test-kb-id", "DATA_SOURCE_ID": "test-ds-id", "AWS_REGION": "eu-west-2"}
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
def s3_event():
    """Mock S3 event"""
    return {
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


@pytest.fixture
def multiple_s3_event():
    """Mock S3 event with multiple records"""
    return {
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


@patch("app.handler.get_bedrock_agent")
@patch("time.time")
def test_handler_success(mock_time, mock_get_bedrock, mock_env, lambda_context, s3_event):
    """Test successful handler execution"""
    mock_time.side_effect = [1000, 1001, 1002, 1003]
    mock_bedrock = mock_get_bedrock.return_value
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    from app.handler import handler

    result = handler(s3_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 1 ingestion job(s) for 1 trigger file(s)" in result["body"]
    mock_bedrock.start_ingestion_job.assert_called_once_with(
        knowledgeBaseId="test-kb-id",
        dataSourceId="test-ds-id",
        description="Auto-sync triggered by S3 ObjectCreated:Put on test-file.pdf",
    )


@patch("app.handler.get_bedrock_agent")
@patch("time.time")
def test_handler_multiple_files(mock_time, mock_get_bedrock, mock_env, lambda_context, multiple_s3_event):
    """Test handler with multiple S3 records"""
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]
    mock_bedrock = mock_get_bedrock.return_value
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    from app.handler import handler

    result = handler(multiple_s3_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 2 ingestion job(s) for 2 trigger file(s)" in result["body"]
    assert mock_bedrock.start_ingestion_job.call_count == 2


@patch("app.handler.get_bedrock_agent")
@patch("time.time")
def test_handler_conflict_exception(mock_time, mock_get_bedrock, mock_env, lambda_context, s3_event):
    """Test handler with ConflictException (job already running)"""
    mock_time.side_effect = [1000, 1001, 1002]
    error = ClientError(
        error_response={"Error": {"Code": "ConflictException", "Message": "Job already running"}},
        operation_name="StartIngestionJob",
    )
    mock_bedrock = mock_get_bedrock.return_value
    mock_bedrock.start_ingestion_job.side_effect = error

    from app.handler import handler

    result = handler(s3_event, lambda_context)

    assert result["statusCode"] == 409
    assert "Files uploaded successfully - processing by existing ingestion job" in result["body"]


@patch("app.handler.get_bedrock_agent")
@patch("time.time")
def test_handler_aws_error(mock_time, mock_get_bedrock, mock_env, lambda_context, s3_event):
    """Test handler with other AWS error"""
    mock_time.side_effect = [1000, 1001, 1002]
    error = ClientError(
        error_response={"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
        operation_name="StartIngestionJob",
    )
    mock_bedrock = mock_get_bedrock.return_value
    mock_bedrock.start_ingestion_job.side_effect = error

    from app.handler import handler

    result = handler(s3_event, lambda_context)

    assert result["statusCode"] == 500
    assert "AWS error: AccessDenied - Access denied" in result["body"]


@patch("app.handler.get_bedrock_agent")
@patch("time.time")
def test_handler_unexpected_error(mock_time, mock_get_bedrock, mock_env, lambda_context, s3_event):
    """Test handler with unexpected error"""
    mock_time.side_effect = [1000, 1001, 1002]
    mock_bedrock = mock_get_bedrock.return_value
    mock_bedrock.start_ingestion_job.side_effect = Exception("Unexpected error")

    from app.handler import handler

    result = handler(s3_event, lambda_context)

    assert result["statusCode"] == 500
    assert "Unexpected error: Unexpected error" in result["body"]


@patch("app.handler.KNOWLEDGEBASE_ID", "")
@patch("app.handler.DATA_SOURCE_ID", "")
def test_handler_missing_env_vars(lambda_context, s3_event):
    """Test handler with missing environment variables"""
    from app.handler import handler

    result = handler(s3_event, lambda_context)

    assert result["statusCode"] == 500
    assert "Configuration error" in result["body"]


def test_handler_invalid_s3_record(mock_env, lambda_context):
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

    from app.handler import handler

    result = handler(invalid_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 0 ingestion job(s) for 0 trigger file(s)" in result["body"]


def test_handler_non_s3_event(mock_env, lambda_context):
    """Test handler with non-S3 event"""
    non_s3_event = {
        "Records": [
            {
                "eventSource": "aws:sns",
                "eventName": "Notification",
            }
        ]
    }

    from app.handler import handler

    result = handler(non_s3_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 0 ingestion job(s) for 0 trigger file(s)" in result["body"]


def test_handler_empty_records(mock_env, lambda_context):
    """Test handler with empty records"""
    empty_event = {"Records": []}

    from app.handler import handler

    result = handler(empty_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 0 ingestion job(s) for 0 trigger file(s)" in result["body"]


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
def test_is_supported_file_type(filename, expected):
    """Test file type allowlist validation"""
    from app.handler import is_supported_file_type

    assert is_supported_file_type(filename) is expected


def test_handler_unsupported_file_type(mock_env, lambda_context):
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

    from app.handler import handler

    result = handler(unsupported_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 0 ingestion job(s) for 0 trigger file(s)" in result["body"]
