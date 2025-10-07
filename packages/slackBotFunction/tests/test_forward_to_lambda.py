import json
import sys
from unittest.mock import Mock, patch

import pytest


@patch("boto3.client")
@patch("app.services.dynamo.store_state_information")
def test_forward_event_to_pull_request_lambda_with_store_pull_request_true(
    mock_store_state_information: Mock,
    mock_boto_client: Mock,
    mock_env: Mock,
):
    """Test triggering async processing"""
    # set up mocks
    mock_lambda_client = Mock(name="lambda_client")

    # Make boto3.client return the right mock depending on service
    def client_side_effect(service_name, *args, **kwargs):
        return mock_lambda_client

    mock_boto_client.side_effect = client_side_effect

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import forward_event_to_pull_request_lambda

    # perform operation
    event_data = {"test": "data", "channel": "C123", "ts": "12345.6789", "text": "foo_bar"}

    with patch("app.utils.handler_utils.get_pull_request_lambda_arn", return_value="output_SlackBotLambdaArn"):
        forward_event_to_pull_request_lambda(
            pull_request_id="123", event=event_data, event_id="evt123", store_pull_request_id=True
        )

        # assertions
        expected_lambda_payload = {
            "pull_request_event": True,
            "slack_event": {
                "event": {"test": "data", "channel": "C123", "ts": "12345.6789", "text": "foo_bar"},
                "event_id": "evt123",
            },
        }

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName="output_SlackBotLambdaArn", InvocationType="Event", Payload=json.dumps(expected_lambda_payload)
        )
        mock_store_state_information.assert_called_once_with(
            item={"pk": "thread#C123#12345.6789", "sk": "pull_request", "pull_request_id": "123"}
        )


@patch("boto3.client")
@patch("app.services.dynamo.store_state_information")
def test_forward_event_to_pull_request_lambda_with_store_pull_request_false(
    mock_store_state_information: Mock,
    mock_boto_client: Mock,
    mock_env: Mock,
):
    """Test triggering async processing"""
    # set up mocks
    mock_lambda_client = Mock(name="lambda_client")

    # Make boto3.client return the right mock depending on service
    def client_side_effect(service_name, *args, **kwargs):
        return mock_lambda_client

    mock_boto_client.side_effect = client_side_effect

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import forward_event_to_pull_request_lambda

    # perform operation
    event_data = {"test": "data", "channel": "C123", "ts": "12345.6789", "text": "foo_bar"}

    with patch("app.utils.handler_utils.get_pull_request_lambda_arn", return_value="output_SlackBotLambdaArn"):
        forward_event_to_pull_request_lambda(
            pull_request_id="123", event=event_data, event_id="evt123", store_pull_request_id=False
        )

        # assertions
        expected_lambda_payload = {
            "pull_request_event": True,
            "slack_event": {
                "event": {"test": "data", "channel": "C123", "ts": "12345.6789", "text": "foo_bar"},
                "event_id": "evt123",
            },
        }

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName="output_SlackBotLambdaArn", InvocationType="Event", Payload=json.dumps(expected_lambda_payload)
        )
        mock_store_state_information.assert_not_called()


@patch("boto3.client")
def test_forward_event_to_pull_request_lambda_processing_error(
    mock_boto_client: Mock,
    mock_env: Mock,
):
    """Test triggering async processing"""
    # set up mocks
    mock_lambda_client = Mock(name="lambda_client")

    # Make boto3.client return the right mock depending on service
    def client_side_effect(service_name, *args, **kwargs):
        return mock_lambda_client

    mock_boto_client.side_effect = client_side_effect

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import forward_event_to_pull_request_lambda

    # perform operation
    event_data = {"test": "data"}
    with patch("app.utils.handler_utils.get_pull_request_lambda_arn") as mock_get_pull_request_lambda_arn:
        mock_get_pull_request_lambda_arn.side_effect = Exception("Error getting lambda arn")
        with pytest.raises(Exception):
            forward_event_to_pull_request_lambda(
                pull_request_id="123", event=event_data, event_id="evt123", store_pull_request_id=False
            )

        # assertions

        mock_lambda_client.invoke.assert_not_called()


@patch("boto3.client")
def test_forward_action_to_pull_request_lambda_processing_error(
    mock_boto_client: Mock,
    mock_env: Mock,
):
    """Test triggering async processing"""
    # set up mocks
    mock_lambda_client = Mock(name="lambda_client")

    # Make boto3.client return the right mock depending on service
    def client_side_effect(service_name, *args, **kwargs):
        return mock_lambda_client

    mock_boto_client.side_effect = client_side_effect

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import forward_action_to_pull_request_lambda

    # perform operation
    mock_body = {"type": "block_actions", "user": {"id": "U123"}, "actions": []}
    with patch("app.utils.handler_utils.get_pull_request_lambda_arn") as mock_get_pull_request_lambda_arn:
        mock_get_pull_request_lambda_arn.side_effect = Exception("Error getting lambda arn")
        with pytest.raises(Exception):
            forward_action_to_pull_request_lambda(pull_request_id="123", body=mock_body)

        # assertions

        mock_lambda_client.invoke.assert_not_called()


@patch("boto3.client")
@patch("app.services.dynamo.store_state_information")
def test_forward_action_to_pull_request_lambda(
    mock_store_state_information: Mock,
    mock_boto_client: Mock,
    mock_env: Mock,
):
    """Test triggering async processing"""
    # set up mocks
    mock_lambda_client = Mock(name="lambda_client")

    # Make boto3.client return the right mock depending on service
    def client_side_effect(service_name, *args, **kwargs):
        return mock_lambda_client

    mock_boto_client.side_effect = client_side_effect

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import forward_action_to_pull_request_lambda

    # perform operation
    mock_body = {"type": "block_actions", "user": {"id": "U123"}, "actions": []}

    with patch("app.utils.handler_utils.get_pull_request_lambda_arn", return_value="output_SlackBotLambdaArn"):
        forward_action_to_pull_request_lambda(pull_request_id="123", body=mock_body)

        # assertions
        expected_lambda_payload = {
            "pull_request_action": True,
            "slack_body": mock_body,
        }

        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName="output_SlackBotLambdaArn", InvocationType="Event", Payload=json.dumps(expected_lambda_payload)
        )
        mock_store_state_information.assert_not_called()
