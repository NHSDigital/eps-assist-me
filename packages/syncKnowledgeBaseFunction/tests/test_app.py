import pytest
import os
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

# Mock boto3.client before importing app to prevent NoRegionError
with patch("boto3.client"):
    import app


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    env_vars = {"KNOWLEDGEBASE_ID": "test-kb-id", "DATA_SOURCE_ID": "test-ds-id"}
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
                "s3": {"bucket": {"name": "test-bucket"}, "object": {"key": "test-file.pdf", "size": 1024}},
            }
        ]
    }


@patch("app.bedrock_agent")
@patch("time.time")
def test_handler_success(mock_time, mock_bedrock, mock_env, lambda_context, s3_event):
    """Test successful handler execution"""
    mock_time.side_effect = [1000, 1001, 1002, 1003]
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    result = app.handler(s3_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 1 ingestion job(s) for 1 trigger file(s)" in result["body"]
    mock_bedrock.start_ingestion_job.assert_called_once_with(
        knowledgeBaseId="test-kb-id",
        dataSourceId="test-ds-id",
        description="Auto-sync triggered by S3 ObjectCreated:Put on test-file.pdf",
    )


@patch("app.bedrock_agent")
def test_handler_missing_env_vars(mock_bedrock, lambda_context, s3_event):
    """Test handler with missing environment variables"""
    with patch.dict(os.environ, {}, clear=True):
        result = app.handler(s3_event, lambda_context)

        assert result["statusCode"] == 500
        assert result["body"] == "Configuration error"
        mock_bedrock.start_ingestion_job.assert_not_called()


@patch("app.bedrock_agent")
def test_handler_conflict_exception(mock_bedrock, mock_env, lambda_context, s3_event):
    """Test handler with ConflictException"""
    error = ClientError(
        error_response={"Error": {"Code": "ConflictException", "Message": "Job already running"}},
        operation_name="StartIngestionJob",
    )
    mock_bedrock.start_ingestion_job.side_effect = error

    result = app.handler(s3_event, lambda_context)

    assert result["statusCode"] == 409
    assert "processing by existing ingestion job" in result["body"]


@patch("app.bedrock_agent")
def test_handler_other_client_error(mock_bedrock, mock_env, lambda_context, s3_event):
    """Test handler with other ClientError"""
    error = ClientError(
        error_response={"Error": {"Code": "ValidationException", "Message": "Invalid request"}},
        operation_name="StartIngestionJob",
    )
    mock_bedrock.start_ingestion_job.side_effect = error

    result = app.handler(s3_event, lambda_context)

    assert result["statusCode"] == 500
    assert "AWS error: ValidationException" in result["body"]


@patch("app.bedrock_agent")
def test_handler_unexpected_error(mock_bedrock, mock_env, lambda_context, s3_event):
    """Test handler with unexpected error"""
    mock_bedrock.start_ingestion_job.side_effect = Exception("Unexpected error")

    result = app.handler(s3_event, lambda_context)

    assert result["statusCode"] == 500
    assert "Unexpected error: Unexpected error" in result["body"]


@patch("app.bedrock_agent")
def test_handler_invalid_s3_record(mock_bedrock, mock_env, lambda_context):
    """Test handler with invalid S3 record"""
    invalid_event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {"bucket": {}, "object": {"key": "test-file.pdf"}},
            }
        ]
    }

    result = app.handler(invalid_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 0 ingestion job(s) for 0 trigger file(s)" in result["body"]
    mock_bedrock.start_ingestion_job.assert_not_called()


@patch("app.bedrock_agent")
def test_handler_non_s3_event(mock_bedrock, mock_env, lambda_context):
    """Test handler with non-S3 event"""
    non_s3_event = {"Records": [{"eventSource": "aws:sns", "eventName": "Notification"}]}

    result = app.handler(non_s3_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 0 ingestion job(s) for 0 trigger file(s)" in result["body"]
    mock_bedrock.start_ingestion_job.assert_not_called()


@patch("app.bedrock_agent")
@patch("time.time")
def test_handler_multiple_records(mock_time, mock_bedrock, mock_env, lambda_context):
    """Test handler with multiple S3 records"""
    mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005]
    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    multi_event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {"bucket": {"name": "test-bucket"}, "object": {"key": "file1.pdf", "size": 1024}},
            },
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectRemoved:Delete",
                "s3": {"bucket": {"name": "test-bucket"}, "object": {"key": "file2.pdf", "size": 2048}},
            },
        ]
    }

    result = app.handler(multi_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 2 ingestion job(s) for 2 trigger file(s)" in result["body"]
    assert mock_bedrock.start_ingestion_job.call_count == 2


@patch("app.bedrock_agent")
def test_handler_empty_records(mock_bedrock, mock_env, lambda_context):
    """Test handler with empty records"""
    empty_event = {"Records": []}

    result = app.handler(empty_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 0 ingestion job(s) for 0 trigger file(s)" in result["body"]
    mock_bedrock.start_ingestion_job.assert_not_called()


@patch("app.bedrock_agent")
def test_handler_missing_records(mock_bedrock, mock_env, lambda_context):
    """Test handler with missing Records key"""
    no_records_event = {}

    result = app.handler(no_records_event, lambda_context)

    assert result["statusCode"] == 200
    assert "Successfully triggered 0 ingestion job(s) for 0 trigger file(s)" in result["body"]
    mock_bedrock.start_ingestion_job.assert_not_called()


@patch("app.bedrock_agent")
def test_handler_missing_object_size(mock_bedrock, mock_env, lambda_context):
    """Test handler with missing object size"""
    event_no_size = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {"bucket": {"name": "test-bucket"}, "object": {"key": "test-file.pdf"}},
            }
        ]
    }

    mock_bedrock.start_ingestion_job.return_value = {
        "ingestionJob": {"ingestionJobId": "job-123", "status": "STARTING"}
    }

    result = app.handler(event_no_size, lambda_context)

    assert result["statusCode"] == 200
    mock_bedrock.start_ingestion_job.assert_called_once()


@patch("app.bedrock_agent")
def test_handler_partial_env_vars(mock_bedrock, lambda_context, s3_event):
    """Test handler with only one environment variable"""
    with patch.dict(os.environ, {"KNOWLEDGEBASE_ID": "test-kb-id"}, clear=True):
        result = app.handler(s3_event, lambda_context)

        assert result["statusCode"] == 500
        assert result["body"] == "Configuration error"


@patch("app.bedrock_agent")
def test_handler_client_error_no_message(mock_bedrock, mock_env, lambda_context, s3_event):
    """Test handler with ClientError missing message"""
    error = ClientError(error_response={"Error": {"Code": "TestError"}}, operation_name="StartIngestionJob")
    mock_bedrock.start_ingestion_job.side_effect = error

    result = app.handler(s3_event, lambda_context)

    assert result["statusCode"] == 500
    assert "AWS error: TestError" in result["body"]


def test_module_imports():
    """Test that all required modules can be imported"""
    assert hasattr(app, "handler")
    assert hasattr(app, "logger")
    assert hasattr(app, "bedrock_agent")
