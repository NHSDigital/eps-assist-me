import pytest
import json
from unittest.mock import Mock, patch
import os
import sys


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    env_vars = {
        "SLACK_BOT_TOKEN_PARAMETER": "/test/bot-token",
        "SLACK_SIGNING_SECRET_PARAMETER": "/test/signing-secret",
        "SLACK_BOT_STATE_TABLE": "test-bot-state-table",
        "KNOWLEDGEBASE_ID": "test-kb-id",
        "RAG_MODEL_ID": "test-model-id",
        "AWS_REGION": "eu-west-2",
        "GUARD_RAIL_ID": "test-guard-id",
        "GUARD_RAIL_VERSION": "1",
        "AWS_LAMBDA_FUNCTION_NAME": "test-function",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


def clear_modules():
    """Clear app modules from cache"""
    modules_to_clear = [k for k in sys.modules.keys() if k.startswith("app")]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_bolt.App")
def test_get_app_creates_instance(mock_app_class, mock_boto_resource, mock_get_parameter, mock_env):
    """Test that get_app creates and returns app instance"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app = Mock()
    mock_app_class.return_value = mock_app

    clear_modules()

    from app.slack.slack_handlers import get_app

    # First call should create the app
    result1 = get_app()
    assert result1 == mock_app
    mock_app_class.assert_called_once()

    # Second call should return the same instance
    result2 = get_app()
    assert result2 == mock_app
    # Should still only be called once (cached)
    mock_app_class.assert_called_once()


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_bolt.App")
def test_app_proxy_delegates_to_get_app(mock_app_class, mock_boto_resource, mock_get_parameter, mock_env):
    """Test that AppProxy delegates attribute access to the app instance"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app = Mock()
    mock_app.some_method = Mock(return_value="test_result")
    mock_app_class.return_value = mock_app

    clear_modules()

    from app.slack.slack_handlers import app

    # Test that accessing attributes on app proxy works
    result = app.some_method()
    assert result == "test_result"
    mock_app.some_method.assert_called_once()


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_bolt.App")
@patch("boto3.client")
@patch("time.time")
def test_setup_handlers_registers_correctly(
    mock_time, mock_boto_client, mock_app_class, mock_boto_resource, mock_get_parameter, mock_env
):
    """Test that _setup_handlers registers the correct handlers"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    mock_time.return_value = 1000
    # Mock DynamoDB
    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table

    # Mock Lambda client
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    # Mock Slack App
    mock_app = Mock()
    mock_app_class.return_value = mock_app

    clear_modules()

    from app.slack.slack_handlers import get_app

    # This will trigger _setup_handlers
    app_instance = get_app()

    # Verify that middleware and event handlers were registered
    assert app_instance.middleware.called
    assert app_instance.event.called

    # Check that event handlers were registered for the right events
    event_calls = [call[0][0] for call in app_instance.event.call_args_list]
    assert "app_mention" in event_calls
    assert "message" in event_calls
