"""
unit tests for bedrockLoggingConfigFunction handler
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock
from app.handler import handler, send_response


@pytest.fixture
def mock_context():
    """mock lambda context"""
    context = MagicMock()
    context.log_stream_name = "test-log-stream"
    return context


@pytest.fixture
def base_event():
    """base cloudformation custom resource event"""
    return {
        "ResponseURL": "https://cloudformation-response.example.com",
        "StackId": "arn:aws:cloudformation:region:account:stack/stack-name/guid",
        "RequestId": "unique-request-id",
        "LogicalResourceId": "BedrockLoggingConfig",
        "ResourceProperties": {
            "CloudWatchLogGroupName": "/aws/bedrock/test/model-invocations",
            "CloudWatchRoleArn": "arn:aws:iam::123456789012:role/BedrockLoggingRole",
            "TextDataDeliveryEnabled": "true",
            "ImageDataDeliveryEnabled": "true",
            "EmbeddingDataDeliveryEnabled": "true",
        },
    }


class TestSendResponse:
    """test cloudformation response signaling"""

    @patch("app.handler.http")
    def test_send_response_success(self, mock_http, mock_context):
        """test successful response to cloudformation"""
        event = {
            "ResponseURL": "https://test.url",
            "StackId": "stack-123",
            "RequestId": "req-123",
            "LogicalResourceId": "resource-123",
        }

        send_response(event, mock_context, "SUCCESS", {"key": "value"}, "physical-id")

        assert mock_http.request.called
        args = mock_http.request.call_args
        assert args[0][0] == "PUT"
        assert args[0][1] == "https://test.url"

        body = json.loads(args[1]["body"])
        assert body["Status"] == "SUCCESS"
        assert body["PhysicalResourceId"] == "physical-id"
        assert body["Data"] == {"key": "value"}

    @patch("app.handler.http")
    def test_send_response_failure(self, mock_http, mock_context):
        """test failure response to cloudformation"""
        event = {
            "ResponseURL": "https://test.url",
            "StackId": "stack-123",
            "RequestId": "req-123",
            "LogicalResourceId": "resource-123",
        }

        send_response(event, mock_context, "FAILED", {}, reason="test error")

        body = json.loads(mock_http.request.call_args[1]["body"])
        assert body["Status"] == "FAILED"
        assert body["Reason"] == "test error"


class TestHandlerLoggingDisabled:
    """test handler when logging is disabled"""

    @patch("app.handler.boto3.client")
    @patch("app.handler.send_response")
    @patch.dict(os.environ, {"ENABLE_LOGGING": "false"})
    def test_create_with_logging_disabled(self, mock_send_response, mock_boto3, base_event, mock_context):
        """test create request deletes configuration when logging disabled"""
        base_event["RequestType"] = "Create"
        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock

        handler(base_event, mock_context)

        # should call delete to remove any existing configuration
        mock_bedrock.delete_model_invocation_logging_configuration.assert_called_once()
        mock_send_response.assert_called_once()
        args = mock_send_response.call_args[0]
        assert args[2] == "SUCCESS"
        assert "disabled via environment variable" in args[3]["Message"]

    @patch("app.handler.boto3.client")
    @patch("app.handler.send_response")
    @patch.dict(os.environ, {"ENABLE_LOGGING": "FALSE"})
    def test_logging_disabled_case_insensitive(self, mock_send_response, mock_boto3, base_event, mock_context):
        """test logging disabled is case insensitive"""
        base_event["RequestType"] = "Create"
        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock

        handler(base_event, mock_context)

        # should call delete to remove any existing configuration
        mock_bedrock.delete_model_invocation_logging_configuration.assert_called_once()
        assert mock_send_response.called
        args = mock_send_response.call_args[0]
        assert args[2] == "SUCCESS"


class TestHandlerCreate:
    """test handler create operations"""

    @patch("app.handler.boto3.client")
    @patch("app.handler.send_response")
    @patch.dict(os.environ, {"ENABLE_LOGGING": "true"})
    def test_create_success(self, mock_send_response, mock_boto3, base_event, mock_context):
        """test successful create request"""
        base_event["RequestType"] = "Create"
        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock
        mock_bedrock.put_model_invocation_logging_configuration.return_value = {}

        handler(base_event, mock_context)

        mock_bedrock.put_model_invocation_logging_configuration.assert_called_once()
        call_args = mock_bedrock.put_model_invocation_logging_configuration.call_args[1]

        assert call_args["loggingConfig"]["textDataDeliveryEnabled"] is True
        assert call_args["loggingConfig"]["imageDataDeliveryEnabled"] is True
        assert call_args["loggingConfig"]["embeddingDataDeliveryEnabled"] is True
        assert call_args["loggingConfig"]["cloudWatchConfig"]["logGroupName"] == "/aws/bedrock/test/model-invocations"

        mock_send_response.assert_called_once()
        assert mock_send_response.call_args[0][2] == "SUCCESS"

    @patch("app.handler.boto3.client")
    @patch("app.handler.send_response")
    @patch.dict(os.environ, {"ENABLE_LOGGING": "true"})
    def test_create_data_delivery_flags(self, mock_send_response, mock_boto3, base_event, mock_context):
        """test create respects data delivery flags"""
        base_event["RequestType"] = "Create"
        base_event["ResourceProperties"]["TextDataDeliveryEnabled"] = "false"
        base_event["ResourceProperties"]["ImageDataDeliveryEnabled"] = "false"

        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock
        mock_bedrock.put_model_invocation_logging_configuration.return_value = {}

        handler(base_event, mock_context)

        call_args = mock_bedrock.put_model_invocation_logging_configuration.call_args[1]
        assert call_args["loggingConfig"]["textDataDeliveryEnabled"] is False
        assert call_args["loggingConfig"]["imageDataDeliveryEnabled"] is False
        assert call_args["loggingConfig"]["embeddingDataDeliveryEnabled"] is True


class TestHandlerUpdate:
    """test handler update operations"""

    @patch("app.handler.boto3.client")
    @patch("app.handler.send_response")
    @patch.dict(os.environ, {"ENABLE_LOGGING": "true"})
    def test_update_success(self, mock_send_response, mock_boto3, base_event, mock_context):
        """test successful update request"""
        base_event["RequestType"] = "Update"
        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock
        mock_bedrock.put_model_invocation_logging_configuration.return_value = {}

        handler(base_event, mock_context)

        mock_bedrock.put_model_invocation_logging_configuration.assert_called_once()
        mock_send_response.assert_called_once()
        assert mock_send_response.call_args[0][2] == "SUCCESS"


class TestHandlerDelete:
    """test handler delete operations"""

    @patch("app.handler.boto3.client")
    @patch("app.handler.send_response")
    @patch.dict(os.environ, {"ENABLE_LOGGING": "true"})
    def test_delete_success(self, mock_send_response, mock_boto3, base_event, mock_context):
        """test successful delete request"""
        base_event["RequestType"] = "Delete"
        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock

        handler(base_event, mock_context)

        mock_bedrock.delete_model_invocation_logging_configuration.assert_called_once()
        mock_send_response.assert_called_once()
        assert mock_send_response.call_args[0][2] == "SUCCESS"

    @patch("app.handler.boto3.client")
    @patch("app.handler.send_response")
    @patch.dict(os.environ, {"ENABLE_LOGGING": "true"})
    def test_delete_not_found(self, mock_send_response, mock_boto3, base_event, mock_context):
        """test delete when configuration doesn't exist"""
        base_event["RequestType"] = "Delete"
        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock
        mock_bedrock.exceptions.ResourceNotFoundException = Exception
        mock_bedrock.delete_model_invocation_logging_configuration.side_effect = Exception("not found")

        handler(base_event, mock_context)

        # should still succeed
        mock_send_response.assert_called_once()
        assert mock_send_response.call_args[0][2] == "SUCCESS"


class TestHandlerErrors:
    """test handler error handling"""

    @patch("app.handler.boto3.client")
    @patch("app.handler.send_response")
    @patch.dict(os.environ, {"ENABLE_LOGGING": "true"})
    def test_create_bedrock_error(self, mock_send_response, mock_boto3, base_event, mock_context):
        """test create handles bedrock api errors"""
        base_event["RequestType"] = "Create"
        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock
        mock_bedrock.put_model_invocation_logging_configuration.side_effect = Exception("api error")

        handler(base_event, mock_context)

        mock_send_response.assert_called_once()
        assert mock_send_response.call_args[0][2] == "FAILED"
        assert "api error" in mock_send_response.call_args[1]["reason"]

    @patch("app.handler.boto3.client")
    @patch("app.handler.send_response")
    @patch.dict(os.environ, {"ENABLE_LOGGING": "true"})
    def test_unsupported_request_type(self, mock_send_response, mock_boto3, base_event, mock_context):
        """test handler rejects unsupported request types"""
        base_event["RequestType"] = "InvalidType"
        mock_bedrock = MagicMock()
        mock_boto3.return_value = mock_bedrock

        handler(base_event, mock_context)

        mock_send_response.assert_called_once()
        assert mock_send_response.call_args[0][2] == "FAILED"
        assert "unsupported request type" in mock_send_response.call_args[1]["reason"]
