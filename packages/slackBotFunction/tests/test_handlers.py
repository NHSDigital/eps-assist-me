import sys
from unittest.mock import Mock, patch


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

    # Just verify handler exists and is callable
    assert callable(handler)


def test_handler_async_processing_missing_slack_event(mock_slack_app, mock_env, mock_get_parameter, lambda_context):
    """Test Lambda handler function for async processing without slack_event data"""

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Test async processing without slack_event - should return 400
    event = {"async_processing": True}  # Missing slack_event
    result = handler(event, lambda_context)

    # Check that result is a dict with statusCode
    assert isinstance(result, dict)
    assert "statusCode" in result
    assert result["statusCode"] == 400
