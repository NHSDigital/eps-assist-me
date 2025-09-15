import sys
from unittest.mock import Mock, patch
from app.slack.slack_handlers import trigger_async_processing


def test_handler_normal_event(mock_slack_app, mock_env, mock_get_parameter, lambda_context):
    """Test Lambda handler function for normal Slack events"""
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    with patch("app.handler.SlackRequestHandler") as mock_handler_class:
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.handle.return_value = {"statusCode": 200}

        event = {"body": "test event"}
        result = handler(event, lambda_context)

        mock_handler.handle.assert_called_once_with(event, lambda_context)
        assert result["statusCode"] == 200


@patch("app.slack.slack_events.process_async_slack_event")
def test_handler_async_processing(mock_process, mock_get_parameter, mock_slack_app, mock_env, lambda_context):
    """Test Lambda handler function for async processing"""

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    slack_event_data = {
        "event": {"text": "test", "user": "U123", "channel": "C456", "ts": "1234567890.123"},
        "event_id": "123",
        "bot_token": "test-token",
    }
    event = {"async_processing": True, "slack_event": slack_event_data}
    result = handler(event, lambda_context)

    mock_process.assert_called_once_with(slack_event_data)
    assert result["statusCode"] == 200


@patch("boto3.client")
def test_trigger_async_processing(
    mock_boto_client,
    mock_slack_app,
    mock_env,
    mock_get_parameter,
):
    """Test triggering async processing"""
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    event_data = {"test": "data"}
    trigger_async_processing(event_data)

    mock_boto_client.assert_called_once_with("lambda")
    mock_lambda_client.invoke.assert_called_once()


def test_handler_async_processing_missing_slack_event(mock_slack_app, mock_env, mock_get_parameter, lambda_context):
    """Test Lambda handler function for async processing without slack_event data"""

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Test async processing without slack_event - should return 400
    event = {"async_processing": True}  # Missing slack_event
    result = handler(event, lambda_context)

    assert result["statusCode"] == 400
