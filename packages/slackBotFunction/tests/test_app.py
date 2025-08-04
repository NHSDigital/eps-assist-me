import pytest
import json
from unittest.mock import Mock, patch
from moto import mock_aws
import boto3
import os
import sys


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    env_vars = {
        "SLACK_BOT_TOKEN_PARAMETER": "/test/bot-token",
        "SLACK_SIGNING_SECRET_PARAMETER": "/test/signing-secret",
        "SLACK_SLASH_COMMAND": "/ask-eps",
        "KNOWLEDGEBASE_ID": "test-kb-id",
        "RAG_MODEL_ID": "test-model-id",
        "AWS_REGION": "eu-west-2",
        "GUARD_RAIL_ID": "test-guard-id",
        "GUARD_RAIL_VERSION": "1",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_ssm_parameters():
    """Mock SSM parameters"""
    with mock_aws():
        client = boto3.client("ssm", region_name="eu-west-2")
        client.put_parameter(
            Name="/test/bot-token",
            Value=json.dumps({"token": "test-bot-token"}),
            Type="SecureString",
        )
        client.put_parameter(
            Name="/test/signing-secret",
            Value=json.dumps({"secret": "test-signing-secret"}),
            Type="SecureString",
        )
        yield


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.function_name = "test-function"
    context.aws_request_id = "test-request-id"
    return context


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
def test_respond_to_slack_within_3_seconds(mock_get_parameter, mock_app, mock_env):
    """Test Slack acknowledgment function"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import respond_to_slack_within_3_seconds

    body = {"text": "test query"}
    ack = Mock()

    respond_to_slack_within_3_seconds(body, ack)

    ack.assert_called_once_with("\n/ask-eps - Processing Request: test query")


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
def test_respond_to_slack_error(mock_get_parameter, mock_app, mock_env):
    """Test Slack acknowledgment error handling"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import respond_to_slack_within_3_seconds

    body = {}  # Missing 'text' key
    ack = Mock()

    respond_to_slack_within_3_seconds(body, ack)

    ack.assert_called_once_with("/ask-eps - Sorry an error occurred. Please try again later.")


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
def test_process_command_request(mock_get_parameter, mock_app, mock_env):
    """Test command processing function"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    if "app" in sys.modules:
        del sys.modules["app"]

    with patch("app.get_bedrock_knowledgebase_response") as mock_bedrock:
        mock_bedrock.return_value = {"output": {"text": "test response"}}
        from app import process_command_request

        body = {"text": "test query"}
        respond = Mock()

        process_command_request(respond, body)

        mock_bedrock.assert_called_once_with("test query")
        respond.assert_called_once_with("\n/ask-eps - Response: test response\n")


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.client")
def test_get_bedrock_knowledgebase_response(mock_boto_client, mock_get_parameter, mock_app, mock_env):
    """Test Bedrock knowledge base integration"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    mock_client.retrieve_and_generate.return_value = {"output": {"text": "bedrock response"}}

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import get_bedrock_knowledgebase_response

    result = get_bedrock_knowledgebase_response("test query")

    mock_boto_client.assert_called_once_with(service_name="bedrock-agent-runtime", region_name="eu-west-2")
    mock_client.retrieve_and_generate.assert_called_once()
    assert result["output"]["text"] == "bedrock response"


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
def test_handler(mock_get_parameter, mock_app, mock_env, lambda_context):
    """Test Lambda handler function"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    if "app" in sys.modules:
        del sys.modules["app"]

    with patch("app.SlackRequestHandler") as mock_handler_class:
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.handle.return_value = {"statusCode": 200}

        from app import handler

        event = {"body": "test event"}
        result = handler(event, lambda_context)

        mock_handler.handle.assert_called_once_with(event, lambda_context)
        assert result["statusCode"] == 200
