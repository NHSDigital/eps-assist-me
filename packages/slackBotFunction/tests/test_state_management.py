import sys
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError


@patch("app.services.dynamo.store_state_information")
def test_is_duplicate_event(
    mock_store_state_information,
    mock_env,
):
    """Test duplicate event detection with conditional put"""
    # Mock ConditionalCheckFailedException

    error = ClientError(error_response={"Error": {"Code": "ConditionalCheckFailedException"}}, operation_name="PutItem")
    mock_store_state_information.side_effect = error

    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]

    from app.utils.handler_utils import is_duplicate_event

    result = is_duplicate_event("test-event")
    assert result is True


@patch("app.services.dynamo.store_state_information")
def test_is_duplicate_event_client_error(
    mock_store_state_information,
    mock_env,
):
    """Test is_duplicate_event handles other ClientError"""

    error = ClientError(error_response={"Error": {"Code": "SomeOtherError"}}, operation_name="PutItem")
    mock_store_state_information.side_effect = error

    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]

    from app.utils.handler_utils import is_duplicate_event

    result = is_duplicate_event("test-event")
    assert result is False


@patch("app.services.dynamo.store_state_information")
def test_is_duplicate_event_no_item(
    mock_store_state_information,
    mock_env,
):
    """Test is_duplicate_event when no item exists (successful put)"""
    # put_item succeeds (no exception)

    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]

    from app.utils.handler_utils import is_duplicate_event

    result = is_duplicate_event("test-event")
    assert result is False


@patch("boto3.client")
def test_trigger_async_processing_error(mock_boto_client, mock_env):
    """Test trigger_async_processing handles Lambda invoke errors"""
    mock_lambda_client = Mock()
    mock_lambda_client.invoke.side_effect = Exception("Lambda invoke error")
    mock_boto_client.return_value = mock_lambda_client

    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.utils.handler_utils import trigger_async_processing

    event_data = {"test": "data"}
    # Should not raise exception even if Lambda invoke fails
    trigger_async_processing(event_data)

    mock_boto_client.assert_called_once_with("lambda")
    mock_lambda_client.invoke.assert_called_once()


@patch("boto3.client")
def test_trigger_async_processing(
    mock_boto_client,
    mock_env,
):
    """Test triggering async processing"""
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.utils.handler_utils import trigger_async_processing

    event_data = {"test": "data"}
    trigger_async_processing(event_data)

    mock_boto_client.assert_called_once_with("lambda")
    mock_lambda_client.invoke.assert_called_once()
