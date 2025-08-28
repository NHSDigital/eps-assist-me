import json
import sys
from unittest.mock import Mock, patch


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_log_request(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test middleware function behavior"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app" in sys.modules:
        del sys.modules["app"]

    # Test that the middleware function exists and can be imported
    from app.slack.slack_handlers import setup_handlers

    assert callable(setup_handlers)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handlers_exist(mock_boto_resource, mock_get_parameter, mock_app_class, mock_env):
    """Test that handlers exist and are registered"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    mock_app_instance = Mock()
    mock_app_class.return_value = mock_app_instance

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    import app.handler  # noqa: F401

    # Verify handlers were registered
    mock_app_instance.event.assert_called()
