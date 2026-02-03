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
                "body": json.dumps(
                    {
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
                )
            }
        ]
    }


@pytest.fixture
def s3_event_markdown():
    return {
        "Records": [
            {
                "body": json.dumps(
                    {
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
                )
            }
        ]
    }


@pytest.fixture
def s3_event_unsupported():
    return {
        "Records": [
            {
                "body": json.dumps(
                    {
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
                )
            }
        ]
    }


@pytest.fixture
def multiple_s3_event():
    return {
        "Records": [
            {
                "body": json.dumps(
                    {
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
                )
            }
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

        event = {"Records": [{"body": json.dumps({"Records": [{"Records": [{"eventSource": "aws:s3", "s3": {}}]}]})}]}

        response = handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["skipped"] == 1

    @patch("app.services.converter.convert_document_to_markdown")
    @patch("app.services.s3_client.download_from_s3")
    def test_handler_handles_conversion_failure(
        self, mock_download, mock_convert, mock_env, lambda_context, s3_event_pdf
    ):
        from app.handler import handler

        mock_convert.return_value = False

        response = handler(s3_event_pdf, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["failed"] == 1

    def test_handler_handles_exception(self, mock_env, lambda_context):
        from app.handler import handler

        event = {"Records": [{"body": json.dumps({"Records": [{"invalid": "data"}]})}]}
        response = handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["skipped"] == 1

    @patch("app.services.s3_client.download_from_s3")
    def test_handler_cleans_up_temp_files_on_error(self, mock_download, mock_env, lambda_context, s3_event_pdf):
        from app.handler import handler

        mock_download.side_effect = Exception("Download failed")

        response = handler(s3_event_pdf, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["failed"] == 1 or body["skipped"] == 1


class TestConverter:

    def test_is_convertible_format(self, mock_env):
        from app.services.converter import is_convertible_format

        assert is_convertible_format(".pdf") is True
        assert is_convertible_format(".docx") is True
        assert is_convertible_format(".xlsx") is True
        assert is_convertible_format(".csv") is True
        assert is_convertible_format(".doc") is True
        assert is_convertible_format(".xls") is True
        assert is_convertible_format(".md") is False
        assert is_convertible_format(".exe") is False

    def test_is_passthrough_format(self, mock_env):
        from app.services.converter import is_passthrough_format

        assert is_passthrough_format(".md") is True
        assert is_passthrough_format(".txt") is True
        assert is_passthrough_format(".html") is True
        assert is_passthrough_format(".json") is True
        assert is_passthrough_format(".pdf") is False

    def test_is_supported_format(self, mock_env):
        from app.services.converter import is_supported_format

        assert is_supported_format(".pdf") is True
        assert is_supported_format(".md") is True
        assert is_supported_format(".docx") is True
        assert is_supported_format(".txt") is True
        assert is_supported_format(".exe") is False

    def test_remove_table_columns(self, mock_env):
        from app.services.converter import remove_table_columns

        markdown_table = """| Col1 | Col2 | Col3 | Col4 | Col5 | Col6 |
| --- | --- | --- | --- | --- | --- |
| A | B | C | D | E | F |"""

        result = remove_table_columns(markdown_table)

        # Should have 2 columns left after removing last 4
        assert "| A | B |" in result
        assert "Col5" not in result
        assert "Col6" not in result

    def test_filter_excel_sheets(self, mock_env):
        from app.services.converter import filter_excel_sheets

        markdown_content = """## EPS Dispensing Requirements
Content 1
## Other Sheet
Content 2
## Technical Conformance
Content 3"""

        result = filter_excel_sheets(markdown_content)

        assert "EPS Dispensing Requirements" in result
        assert "Technical Conformance" in result
        assert "Other Sheet" not in result
        assert "Content 1" in result
        assert "Content 3" in result
        assert "Content 2" not in result

    def test_filter_excel_sheets_with_html_entities(self, mock_env):
        from app.services.converter import filter_excel_sheets

        markdown_content = """## EPS &amp; Dispensing Requirements
Content"""

        result = filter_excel_sheets(markdown_content)

        # Should not match due to & not &amp;
        assert result == ""

    @patch("app.services.converter.MarkItDown")
    def test_convert_document_to_markdown_success(self, mock_markitdown, mock_env):
        from app.services.converter import convert_document_to_markdown
        from pathlib import Path
        import tempfile

        mock_result = Mock()
        mock_result.text_content = "# Test Document\nContent"
        mock_markitdown.return_value.convert.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "test.txt"
            input_path.write_text("test")
            output_path = Path(temp_dir) / "output.md"

            result = convert_document_to_markdown(input_path, output_path)

            assert result is True
            assert output_path.exists()
            assert "# Test Document" in output_path.read_text()

    @patch("app.services.converter.MarkItDown")
    def test_convert_document_to_markdown_excel_filtering(self, mock_markitdown, mock_env):
        from app.services.converter import convert_document_to_markdown
        from pathlib import Path
        import tempfile

        mock_result = Mock()
        mock_result.text_content = """## EPS Dispensing Requirements
| A | B | C | D | E | F |
## Other Sheet
Content"""
        mock_markitdown.return_value.convert.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "test.xlsx"
            input_path.write_bytes(b"fake excel")
            output_path = Path(temp_dir) / "output.md"

            result = convert_document_to_markdown(input_path, output_path)

            assert result is True
            content = output_path.read_text()
            assert "EPS Dispensing Requirements" in content
            assert "Other Sheet" not in content

    @patch("app.services.converter.MarkItDown")
    def test_convert_document_to_markdown_unsupported_format(self, mock_markitdown, mock_env):
        from app.services.converter import convert_document_to_markdown
        from pathlib import Path
        import tempfile

        mock_markitdown.return_value.convert.side_effect = Exception("format not supported")

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "test.xyz"
            input_path.write_text("test")
            output_path = Path(temp_dir) / "output.md"

            result = convert_document_to_markdown(input_path, output_path)

            assert result is False

    @patch("app.services.converter.MarkItDown")
    def test_convert_document_to_markdown_corrupted_file(self, mock_markitdown, mock_env):
        from app.services.converter import convert_document_to_markdown
        from pathlib import Path
        import tempfile

        mock_markitdown.return_value.convert.side_effect = Exception("not a zip file")

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "corrupted.docx"
            input_path.write_text("not a real docx")
            output_path = Path(temp_dir) / "output.md"

            result = convert_document_to_markdown(input_path, output_path)

            assert result is False

    @patch("app.services.converter.MarkItDown")
    def test_convert_document_to_markdown_generic_error(self, mock_markitdown, mock_env):
        from app.services.converter import convert_document_to_markdown
        from pathlib import Path
        import tempfile

        mock_markitdown.return_value.convert.side_effect = Exception("Generic error")

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "test.pdf"
            input_path.write_text("test")
            output_path = Path(temp_dir) / "output.md"

            result = convert_document_to_markdown(input_path, output_path)

            assert result is False


class TestS3Client:

    @patch("app.services.s3_client.s3_client")
    def test_download_from_s3(self, mock_s3, mock_env):
        from app.services.s3_client import download_from_s3
        from pathlib import Path
        import tempfile

        def mock_download_file(**kwargs):
            Path(kwargs["Filename"]).write_bytes(b"test content")

        mock_s3.download_file.side_effect = mock_download_file

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "test.pdf"
            download_from_s3("test-bucket", "test-key", local_path)

            mock_s3.download_file.assert_called_once()
            assert local_path.exists()

    @patch("app.services.s3_client.s3_client")
    def test_upload_to_s3(self, mock_s3, mock_env):
        from app.services.s3_client import upload_to_s3
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = Path(temp_dir) / "test.md"
            local_path.write_text("test content")
            upload_to_s3(local_path, "test-bucket", "test-key")

            mock_s3.upload_file.assert_called_once()

    @patch("app.services.s3_client.s3_client")
    def test_copy_s3_object(self, mock_s3, mock_env):
        from app.services.s3_client import copy_s3_object

        copy_s3_object("source-bucket", "source-key", "dest-bucket", "dest-key")

        mock_s3.copy_object.assert_called_once()
        call_args = mock_s3.copy_object.call_args[1]
        assert call_args["Bucket"] == "dest-bucket"
        assert call_args["Key"] == "dest-key"
        assert call_args["CopySource"]["Bucket"] == "source-bucket"
        assert call_args["CopySource"]["Key"] == "source-key"
