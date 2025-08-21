import json
import sys
from unittest.mock import Mock, patch


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_sdk.WebClient")
def test_process_async_slack_event_success(mock_webclient, mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test successful async event processing"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()
    mock_client = Mock()
    mock_webclient.return_value = mock_client

    if "app.util.slack_events" in sys.modules:
        del sys.modules["app.util.slack_events"]

    with patch("app.util.slack_events.query_bedrock") as mock_bedrock, patch(
        "app.util.slack_events.get_conversation_session"
    ) as mock_get_session, patch("boto3.client"):
        mock_bedrock.return_value = {"output": {"text": "AI response"}}
        mock_get_session.return_value = None  # No existing session

        from app.util.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {"text": "<@U123> test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"},
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        process_async_slack_event(slack_event_data)

        mock_client.chat_postMessage.assert_called_once_with(
            channel="C789", text="AI response", thread_ts="1234567890.123"
        )


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_sdk.WebClient")
def test_process_async_slack_event_empty_query(
    mock_webclient, mock_boto_resource, mock_get_parameter, mock_app, mock_env
):
    """Test async event processing with empty query"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()
    mock_client = Mock()
    mock_webclient.return_value = mock_client

    if "app.util.slack_events" in sys.modules:
        del sys.modules["app.util.slack_events"]

    from app.util.slack_events import process_async_slack_event

    slack_event_data = {
        "event": {
            "text": "<@U123>",  # Only mention, no actual query
            "user": "U456",
            "channel": "C789",
            "ts": "1234567890.123",
        },
        "event_id": "evt123",
        "bot_token": "bot-token",
    }

    process_async_slack_event(slack_event_data)

    mock_client.chat_postMessage.assert_called_once_with(
        channel="C789",
        text="Hi there! Please ask me a question and I'll help you find information from our knowledge base.",
        thread_ts="1234567890.123",
    )


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_sdk.WebClient")
def test_process_async_slack_event_error(mock_webclient, mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test async event processing with error"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()
    mock_client = Mock()
    mock_webclient.return_value = mock_client

    if "app.util.slack_events" in sys.modules:
        del sys.modules["app.util.slack_events"]

    if "app.util.slack_events" in sys.modules:
        del sys.modules["app.util.slack_events"]

    with patch("app.util.slack_events.query_bedrock") as mock_bedrock, patch(
        "app.util.slack_events.get_conversation_session"
    ) as mock_get_session, patch("boto3.client"):
        mock_bedrock.side_effect = Exception("Bedrock error")
        mock_get_session.return_value = None  # No existing session

        from app.util.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {"text": "test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"},
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        process_async_slack_event(slack_event_data)

        mock_client.chat_postMessage.assert_called_once_with(
            channel="C789",
            text="Sorry, an error occurred while processing your request. Please try again later.",
            thread_ts="1234567890.123",
        )


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_sdk.WebClient")
def test_process_async_slack_event_with_thread_ts(
    mock_webclient, mock_boto_resource, mock_get_parameter, mock_app, mock_env
):
    """Test async event processing with existing thread_ts"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()
    mock_client = Mock()
    mock_webclient.return_value = mock_client

    if "app.util.slack_events" in sys.modules:
        del sys.modules["app.util.slack_events"]

    if "app.util.slack_events" in sys.modules:
        del sys.modules["app.util.slack_events"]

    with patch("app.util.slack_events.query_bedrock") as mock_bedrock, patch(
        "app.util.slack_events.get_conversation_session"
    ) as mock_get_session, patch("boto3.client"):
        mock_bedrock.return_value = {"output": {"text": "AI response"}}
        mock_get_session.return_value = None  # No existing session

        from app.util.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {
                "text": "<@U123> test question",
                "user": "U456",
                "channel": "C789",
                "ts": "1234567890.123",
                "thread_ts": "1234567888.111",  # Existing thread
            },
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        process_async_slack_event(slack_event_data)

        # Should use the existing thread_ts, not the message ts
        mock_client.chat_postMessage.assert_called_once_with(
            channel="C789", text="AI response", thread_ts="1234567888.111"
        )


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_sdk.WebClient")
def test_regex_text_processing(mock_webclient, mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test regex text processing functionality within process_async_slack_event"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()
    mock_client = Mock()
    mock_webclient.return_value = mock_client

    if "app.util.slack_events" in sys.modules:
        del sys.modules["app.util.slack_events"]

    if "app.util.slack_events" in sys.modules:
        del sys.modules["app.util.slack_events"]

    with patch("app.util.slack_events.query_bedrock") as mock_bedrock, patch(
        "app.util.slack_events.get_conversation_session"
    ) as mock_get_session, patch("boto3.client"):
        mock_bedrock.return_value = {"output": {"text": "AI response"}}
        mock_get_session.return_value = None  # No existing session

        from app.util.slack_events import process_async_slack_event

        # Test that mentions are properly stripped from messages
        slack_event_data = {
            "event": {"text": "<@U123456> test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"},
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        process_async_slack_event(slack_event_data)

        # Verify that the message was processed (query_bedrock was called)
        mock_bedrock.assert_called_once()
        # The actual regex processing happens inside the function
        assert mock_client.chat_postMessage.called
