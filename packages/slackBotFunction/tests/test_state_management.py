import json
import sys
from unittest.mock import Mock, patch


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("time.time")
def test_is_duplicate_event(mock_time, mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test duplicate event detection with conditional put"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_time.return_value = 1000

    # Mock ConditionalCheckFailedException
    from botocore.exceptions import ClientError

    error = ClientError(error_response={"Error": {"Code": "ConditionalCheckFailedException"}}, operation_name="PutItem")
    mock_table.put_item.side_effect = error

    if "app.util.slack_handlers" in sys.modules:
        del sys.modules["app.util.slack_handlers"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]

    from app.util.slack_handlers import is_duplicate_event

    result = is_duplicate_event("test-event")
    assert result is True


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("time.time")
def test_is_duplicate_event_client_error(mock_time, mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test is_duplicate_event handles other ClientError"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_time.return_value = 1000

    # Mock other ClientError (not ConditionalCheckFailedException)
    from botocore.exceptions import ClientError

    error = ClientError(error_response={"Error": {"Code": "SomeOtherError"}}, operation_name="PutItem")
    mock_table.put_item.side_effect = error

    if "app.util.slack_handlers" in sys.modules:
        del sys.modules["app.util.slack_handlers"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]

    from app.util.slack_handlers import is_duplicate_event

    result = is_duplicate_event("test-event")
    assert result is False


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("time.time")
def test_is_duplicate_event_no_item(mock_time, mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test is_duplicate_event when no item exists (successful put)"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_time.return_value = 1000
    # put_item succeeds (no exception)

    if "app.util.slack_handlers" in sys.modules:
        del sys.modules["app.util.slack_handlers"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]

    from app.util.slack_handlers import is_duplicate_event

    result = is_duplicate_event("test-event")
    assert result is False


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_process_async_slack_event_exists(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test process_async_slack_event function exists and is callable"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app.util.slack_events" in sys.modules:
        del sys.modules["app.util.slack_events"]

    from app.util.slack_events import process_async_slack_event

    assert callable(process_async_slack_event)
