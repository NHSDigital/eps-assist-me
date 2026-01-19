import pytest
import os
import json
from unittest.mock import Mock, patch


@pytest.fixture
def mock_env():
    env_vars = {
        "DOCS_BUCKET_NAME": "test-bucket",
        "RAW_PREFIX": "raw/",
        "PROCESSED_PREFIX": "processed/",
        "AWS_REGION": "eu-west-2",
        "AWS_ACCOUNT_ID": "123456789012",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def lambda_context():
    context = Mock()
    context.function_name = "test-preprocessing-function"
    context.aws_request_id = "test-request-id"
    return context


@pytest.fixture
def s3_event_pdf():
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "raw/test-document.pdf", "size": 1024},
                },
            }
        ]
    }


@pytest.fixture
def s3_event_markdown():
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "raw/test-document.md", "size": 512},
                },
            }
        ]
    }


@pytest.fixture
def s3_event_unsupported():
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "raw/test-file.exe", "size": 2048},
                },
            }
        ]
    }


@pytest.fixture
def multiple_s3_event():
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "raw/document1.pdf", "size": 1024},
                },
            },
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "raw/document2.md", "size": 512},
                },
            },
        ]
    }


class TestHandler:

    @patch("app.services.converter.convert_document_to_markdown")
    @patch("app.services.s3_client.download_from_s3")
    @patch("app.services.s3_client.upload_to_s3")
    def test_handler_converts_pdf_successfully(
        self, mock_upload, mock_download, mock_convert, mock_env, lambda_context, s3_event_pdf
    ):
        from app.handler import handler

        mock_convert.return_value = True

        response = handler(s3_event_pdf, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] == 1
        assert mock_download.called
        assert mock_upload.called
        assert mock_convert.called

    @patch("app.services.s3_client.s3_client")
    def test_handler_passes_through_markdown(self, mock_s3, mock_env, lambda_context, s3_event_markdown):
        from app.handler import handler

        response = handler(s3_event_markdown, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] == 1
        assert mock_s3.copy_object.called
        assert not mock_s3.download_file.called

    def test_handler_skips_unsupported_format(self, mock_env, lambda_context, s3_event_unsupported):
        from app.handler import handler

        response = handler(s3_event_unsupported, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["skipped"] == 1

    @patch("app.services.converter.convert_document_to_markdown")
    @patch("app.services.s3_client.download_from_s3")
    @patch("app.services.s3_client.upload_to_s3")
    @patch("app.services.s3_client.copy_s3_object")
    def test_handler_processes_multiple_records(
        self, mock_copy, mock_upload, mock_download, mock_convert, mock_env, lambda_context, multiple_s3_event
    ):
        from app.handler import handler

        mock_convert.return_value = True

        response = handler(multiple_s3_event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["total"] == 2
        assert body["success"] == 2

    def test_handler_handles_empty_records(self, mock_env, lambda_context):
        from app.handler import handler

        event = {"Records": []}
        response = handler(event, lambda_context)

        assert response["statusCode"] == 200

    def test_handler_handles_malformed_event(self, mock_env, lambda_context):
        from app.handler import handler

        event = {"Records": [{"eventSource": "aws:s3", "s3": {}}]}

        response = handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["skipped"] == 1


class TestConverter:

    def test_is_convertible_format(self, mock_env):
        from app.services.converter import is_convertible_format

        assert is_convertible_format(".pdf") is True
        assert is_convertible_format(".docx") is True
        assert is_convertible_format(".md") is False
        assert is_convertible_format(".exe") is False

    def test_is_passthrough_format(self, mock_env):
        from app.services.converter import is_passthrough_format

        assert is_passthrough_format(".md") is True
        assert is_passthrough_format(".txt") is True
        assert is_passthrough_format(".pdf") is False

    def test_is_supported_format(self, mock_env):
        from app.services.converter import is_supported_format

        assert is_supported_format(".pdf") is True
        assert is_supported_format(".md") is True
        assert is_supported_format(".exe") is False
