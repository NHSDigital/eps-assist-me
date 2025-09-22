import json
import sys
from unittest.mock import Mock, patch

import pytest


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
    with pytest.raises(Exception):
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


@patch("boto3.client")
def test_trigger_pull_request_processing(
    mock_boto_client: Mock,
    mock_env: Mock,
):
    """Test triggering async processing"""
    # set up mocks
    mock_cf_client = Mock(name="cloudformation_client")
    mock_lambda_client = Mock(name="lambda_client")

    # Make boto3.client return the right mock depending on service
    def client_side_effect(service_name, *args, **kwargs):
        if service_name == "cloudformation":
            return mock_cf_client
        elif service_name == "lambda":
            return mock_lambda_client
        else:
            raise ValueError(f"Unexpected client: {service_name}")

    mock_boto_client.side_effect = client_side_effect

    mock_cf_client.describe_stacks.return_value = {
        "Stacks": [
            {
                "StackName": "mystack",
                "Outputs": [{"OutputKey": "SlackBotLambdaArn", "OutputValue": "output_SlackBotLambdaArn"}],
            }
        ]
    }

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import trigger_pull_request_processing

    # perform operation
    event_data = {"test": "data"}
    trigger_pull_request_processing(pull_request_id="123", event=event_data, event_id="evt123")

    # assertions
    expected_lambda_payload = {
        "pull_request_processing": True,
        "slack_event": {"event": {"test": "data"}, "event_id": "evt123"},
    }

    mock_lambda_client.invoke.assert_called_once_with(
        FunctionName="output_SlackBotLambdaArn", InvocationType="Event", Payload=json.dumps(expected_lambda_payload)
    )


@patch("boto3.client")
def test_trigger_pull_request_processing_error(
    mock_boto_client: Mock,
    mock_env: Mock,
):
    """Test triggering async processing"""
    # set up mocks
    mock_cf_client = Mock(name="cloudformation_client")
    mock_lambda_client = Mock(name="lambda_client")

    # Make boto3.client return the right mock depending on service
    def client_side_effect(service_name, *args, **kwargs):
        if service_name == "cloudformation":
            return mock_cf_client
        elif service_name == "lambda":
            return mock_lambda_client
        else:
            raise ValueError(f"Unexpected client: {service_name}")

    mock_boto_client.side_effect = client_side_effect

    mock_cf_client.invoke.side_effect = Exception("Lambda invoke error")

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import trigger_pull_request_processing

    # perform operation
    event_data = {"test": "data"}
    with pytest.raises(Exception):
        trigger_pull_request_processing(pull_request_id="123", event=event_data, event_id="evt123")

        # assertions

        mock_lambda_client.invoke.assert_not_called()
