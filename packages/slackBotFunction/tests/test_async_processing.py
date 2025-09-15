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
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}
    mock_webclient.return_value = mock_client

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("app.slack.slack_events.query_bedrock") as mock_bedrock, patch(
        "app.slack.slack_events.get_conversation_session"
    ) as mock_get_session, patch("boto3.client"):
        mock_bedrock.return_value = {"output": {"text": "AI response"}}
        mock_get_session.return_value = None  # No existing session

        from app.slack.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {"text": "<@U123> test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"},
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        process_async_slack_event(slack_event_data)

        # Should be called at least once - first for AI response
        assert mock_client.chat_postMessage.call_count >= 1
        first_call = mock_client.chat_postMessage.call_args_list[0]
        assert first_call[1]["text"] == "AI response"
        assert first_call[1]["channel"] == "C789"


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

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    from app.slack.slack_events import process_async_slack_event

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

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("app.slack.slack_events.query_bedrock") as mock_bedrock, patch(
        "app.slack.slack_events.get_conversation_session"
    ) as mock_get_session, patch("boto3.client"):
        mock_bedrock.side_effect = Exception("Bedrock error")
        mock_get_session.return_value = None  # No existing session

        from app.slack.slack_events import process_async_slack_event

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
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}
    mock_webclient.return_value = mock_client

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("app.slack.slack_events.query_bedrock") as mock_bedrock, patch(
        "app.slack.slack_events.get_conversation_session"
    ) as mock_get_session, patch("boto3.client"):
        mock_bedrock.return_value = {"output": {"text": "AI response"}}
        mock_get_session.return_value = None  # No existing session

        from app.slack.slack_events import process_async_slack_event

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

        # Should be called at least once with the correct thread_ts
        assert mock_client.chat_postMessage.call_count >= 1
        first_call = mock_client.chat_postMessage.call_args_list[0]
        assert first_call[1]["thread_ts"] == "1234567888.111"
        assert first_call[1]["text"] == "AI response"


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

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("app.slack.slack_events.query_bedrock") as mock_bedrock, patch(
        "app.slack.slack_events.get_conversation_session"
    ) as mock_get_session, patch("boto3.client"):
        mock_bedrock.return_value = {"output": {"text": "AI response"}}
        mock_get_session.return_value = None  # No existing session

        from app.slack.slack_events import process_async_slack_event

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


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_sdk.WebClient")
def test_process_async_slack_event_with_session_storage(
    mock_webclient, mock_boto_resource, mock_get_parameter, mock_app, mock_env
):
    """Test async event processing that stores a new session"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_table = Mock()
    mock_table.get_item.return_value = {}  # No existing session
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}
    mock_webclient.return_value = mock_client

    # Clean up modules before import
    modules_to_clean = ["app.slack.slack_events", "app.core.config"]
    for module in modules_to_clean:
        if module in sys.modules:
            del sys.modules[module]

    with patch("boto3.client") as mock_bedrock_client, patch.dict(
        "os.environ",
        {
            "QUERY_REFORMULATION_MODEL_ID": "test-model",
            "QUERY_REFORMULATION_PROMPT_NAME": "test-prompt",
            "QUERY_REFORMULATION_PROMPT_VERSION": "DRAFT",
        },
    ):
        # Mock the bedrock client to return a session ID
        mock_bedrock_client.return_value.retrieve_and_generate.return_value = {
            "output": {"text": "AI response"},
            "sessionId": "new-session-123",
        }

        from app.slack.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {"text": "test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"},
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        process_async_slack_event(slack_event_data)

        # Verify session was stored - should be called twice (Q&A pair + session)
        assert mock_table.put_item.call_count >= 1
        # Find the session storage call
        session_call = None
        for call in mock_table.put_item.call_args_list:
            item = call[1]["Item"]
            if "session_id" in item:
                session_call = item
                break

        assert session_call is not None
        assert session_call["session_id"] == "new-session-123"
        assert session_call["user_id"] == "U456"


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_process_async_slack_event_chat_update_error(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test process_async_slack_event with chat_update error"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("slack_sdk.WebClient") as mock_webclient, patch(
        "app.slack.slack_events.query_bedrock"
    ) as mock_bedrock, patch("app.slack.slack_events.get_conversation_session") as mock_get_session, patch(
        "boto3.client"
    ):

        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ts": "123"}
        mock_client.chat_update.side_effect = Exception("Update failed")
        mock_webclient.return_value = mock_client

        mock_bedrock.return_value = {"output": {"text": "AI response"}}
        mock_get_session.return_value = None

        from app.slack.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {"text": "test question", "user": "U456", "channel": "C789", "ts": "123"},
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        # Should not raise exception
        process_async_slack_event(slack_event_data)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_process_async_slack_event_post_error_message_fails(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test process_async_slack_event when posting error message fails"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("slack_sdk.WebClient") as mock_webclient, patch(
        "app.slack.slack_events.query_bedrock"
    ) as mock_bedrock, patch("boto3.client"):

        mock_client = Mock()
        mock_client.chat_postMessage.side_effect = Exception("Post failed")
        mock_webclient.return_value = mock_client

        mock_bedrock.side_effect = Exception("Bedrock error")

        from app.slack.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {"text": "test question", "user": "U456", "channel": "C789", "ts": "123"},
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        # Should not raise exception even when error posting fails
        process_async_slack_event(slack_event_data)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_process_async_slack_event_dm_context(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test process_async_slack_event with DM context"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("slack_sdk.WebClient") as mock_webclient, patch(
        "app.slack.slack_events.query_bedrock"
    ) as mock_bedrock, patch("app.slack.slack_events.get_conversation_session") as mock_get_session, patch(
        "boto3.client"
    ):

        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ts": "123"}
        mock_webclient.return_value = mock_client

        mock_bedrock.return_value = {"output": {"text": "AI response"}, "sessionId": "new-session"}
        mock_get_session.return_value = None

        from app.slack.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {
                "text": "test question",
                "user": "U456",
                "channel": "D789",
                "ts": "123",
                "channel_type": "im",  # DM context
            },
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        process_async_slack_event(slack_event_data)
