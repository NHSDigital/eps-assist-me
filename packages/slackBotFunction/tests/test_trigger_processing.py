import sys
from unittest.mock import Mock, patch


@patch("boto3.client")
def test_trigger_async_processing_error(mock_boto_client: Mock, mock_env: Mock):
    """Test trigger_async_processing handles Lambda invoke errors"""
    # set up mocks
    mock_lambda_client = Mock()
    mock_lambda_client.invoke.side_effect = Exception("Lambda invoke error")
    mock_boto_client.return_value = mock_lambda_client

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import trigger_async_processing

    # perform operation
    event_data = {"test": "data"}
    # Should not raise exception even if Lambda invoke fails
    trigger_async_processing(event=event_data, event_id="evt123")

    # assertions
    mock_boto_client.assert_called_once_with("lambda")
    mock_lambda_client.invoke.assert_called_once()


@patch("boto3.client")
def test_trigger_async_processing(
    mock_boto_client: Mock,
    mock_env: Mock,
):
    """Test triggering async processing"""
    # set up mocks
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import trigger_async_processing

    # perform operation
    event_data = {"test": "data"}
    trigger_async_processing(event=event_data, event_id="evt123")

    # assertions
    mock_boto_client.assert_called_once_with("lambda")
    mock_lambda_client.invoke.assert_called_once()
