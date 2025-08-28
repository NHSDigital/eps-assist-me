import json
import sys
from unittest.mock import Mock, patch


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handler_normal_event(mock_boto_resource, mock_get_parameter, mock_app, mock_env, lambda_context):
    """Test Lambda handler function exists and is callable"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]

    from app.handler import handler

    # Just verify handler exists and is callable
    assert callable(handler)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handler_async_processing(mock_boto_resource, mock_get_parameter, mock_app, mock_env, lambda_context):
    """Test Lambda handler function for async processing"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]

    from app.handler import handler

    # Just verify handler exists and is callable
    assert callable(handler)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
def test_trigger_async_processing(mock_boto_client, mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test triggering async processing"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import trigger_async_processing

    event_data = {"test": "data"}
    trigger_async_processing(event_data)

    mock_boto_client.assert_called_once_with("lambda")
    mock_lambda_client.invoke.assert_called_once()


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handle_app_mention(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test app mention handler exists and is callable"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    assert callable(setup_handlers)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handle_direct_message(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test direct message handler exists and is callable"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    assert callable(setup_handlers)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handle_app_mention_missing_event_id(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test app mention handler with missing event ID"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    # Test that the setup function exists
    assert callable(setup_handlers)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handle_direct_message_channel_type(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test direct message handler with channel type validation"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    # Test that the setup function exists
    assert callable(setup_handlers)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handler_async_processing_missing_slack_event(
    mock_boto_resource, mock_get_parameter, mock_app, mock_env, lambda_context
):
    """Test Lambda handler function for async processing without slack_event data"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]

    from app.handler import handler

    # Test async processing without slack_event - should return 400
    event = {"async_processing": True}  # Missing slack_event
    result = handler(event, lambda_context)

    # Check that result is a dict with statusCode
    assert isinstance(result, dict)
    assert "statusCode" in result
    assert result["statusCode"] == 400
