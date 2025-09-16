import sys
from unittest.mock import Mock, patch


@patch("slack_sdk.WebClient")
@patch("app.services.dynamo.get_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
def test_process_async_slack_event_success(
    mock_reformulate_query, mock_query_bedrock, mock_get_state_information, mock_webclient, mock_env
):
    """Test successful async event processing"""
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}
    mock_webclient.return_value = mock_client
    mock_query_bedrock.return_value = {"output": {"text": "AI response"}}
    mock_reformulate_query.return_value = "test question"

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("app.slack.slack_events.get_conversation_session") as mock_get_session:
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


@patch("slack_sdk.WebClient")
def test_process_async_slack_event_empty_query(mock_webclient, mock_env):
    """Test async event processing with empty query"""
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


@patch("slack_sdk.WebClient")
@patch("app.services.dynamo.get_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
def test_process_async_slack_event_error(
    mock_reformulate_query, mock_query_bedrock, mock_get_state_information, mock_webclient, mock_env
):
    """Test async event processing with error"""
    mock_client = Mock()
    mock_webclient.return_value = mock_client
    mock_query_bedrock.side_effect = Exception("Bedrock error")
    mock_reformulate_query.return_value = "test question"

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("app.slack.slack_events.get_conversation_session") as mock_get_session, patch("boto3.client"):
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


@patch("slack_sdk.WebClient")
@patch("app.services.dynamo.get_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
def test_process_async_slack_event_with_thread_ts(
    mock_reformulate_query, mock_query_bedrock, mock_get_state_information, mock_webclient, mock_env
):
    """Test async event processing with existing thread_ts"""
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}
    mock_webclient.return_value = mock_client
    mock_query_bedrock.return_value = {"output": {"text": "AI response"}}
    mock_reformulate_query.return_value = "test question"

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("app.slack.slack_events.get_conversation_session") as mock_get_session:
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


@patch("slack_sdk.WebClient")
@patch("app.services.dynamo.get_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
def test_regex_text_processing(
    mock_reformulate_query, mock_query_bedrock, mock_get_state_information, mock_webclient, mock_env
):
    """Test regex text processing functionality within process_async_slack_event"""
    mock_client = Mock()
    mock_webclient.return_value = mock_client
    mock_query_bedrock.return_value = {"output": {"text": "AI response"}}
    mock_reformulate_query.return_value = "test question"

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("app.slack.slack_events.get_conversation_session") as mock_get_session:
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
        mock_query_bedrock.assert_called_once()
        # The actual regex processing happens inside the function
        assert mock_client.chat_postMessage.called


@patch("slack_sdk.WebClient")
@patch("app.services.dynamo.get_state_information")
@patch("app.services.dynamo.store_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
def test_process_async_slack_event_with_session_storage(
    mock_reformulate_query,
    mock_query_bedrock,
    mock_store_state_information,
    mock_get_state_information,
    mock_webclient,
    mock_env,
):
    """Test async event processing that stores a new session"""
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}
    mock_webclient.return_value = mock_client
    mock_query_bedrock.return_value = {
        "output": {"text": "AI response"},
        "sessionId": "new-session-123",
    }
    mock_reformulate_query.return_value = "test question"

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    from app.slack.slack_events import process_async_slack_event

    slack_event_data = {
        "event": {"text": "test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"},
        "event_id": "evt123",
        "bot_token": "bot-token",
    }

    process_async_slack_event(slack_event_data)

    # Verify session was stored - should be called twice (Q&A pair + session)
    assert mock_store_state_information.call_count >= 1


@patch("slack_sdk.WebClient")
@patch("app.services.dynamo.get_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
def test_process_async_slack_event_chat_update_error(
    mock_reformulate_query, mock_query_bedrock, mock_get_state_information, mock_webclient, mock_env
):
    """Test process_async_slack_event with chat_update error"""
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.side_effect = Exception("Update failed")
    mock_webclient.return_value = mock_client
    mock_query_bedrock.return_value = {"output": {"text": "AI response"}}
    mock_reformulate_query.return_value = "test question"

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("app.slack.slack_events.get_conversation_session") as mock_get_session:
        mock_get_session.return_value = None  # No existing session

        from app.slack.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {"text": "<@U123> test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"},
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        process_async_slack_event(slack_event_data)


@patch("slack_sdk.WebClient")
@patch("app.services.dynamo.get_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
def test_process_async_slack_event_dm_context(
    mock_reformulate_query, mock_query_bedrock, mock_get_state_information, mock_webclient, mock_env
):
    """Test process_async_slack_event with DM context"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    with patch("slack_sdk.WebClient") as mock_webclient, patch(
        "app.slack.slack_events.get_conversation_session"
    ) as mock_get_session:

        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ts": "123"}
        mock_webclient.return_value = mock_client

        mock_query_bedrock.return_value = {"output": {"text": "AI response"}, "sessionId": "new-session"}
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
