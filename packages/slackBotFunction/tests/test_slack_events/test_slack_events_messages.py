import sys
import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def mock_logger():
    return MagicMock()


@patch("app.utils.handler_utils.forward_to_pull_request_lambda")
def test_process_async_slack_event_normal_message(
    mock_forward_to_pull_request_lambda: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test successful async event processing"""
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_event

    # perform operation
    slack_event_data = {"text": "<@U123> test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"}
    with patch("app.slack.slack_events.process_feedback_event") as mock_process_feedback_event, patch(
        "app.slack.slack_events.process_slack_message"
    ) as mock_process_slack_message:
        process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)
        mock_forward_to_pull_request_lambda.assert_not_called()
        mock_process_feedback_event.assert_not_called()
        mock_process_slack_message.assert_called_once_with(
            event=slack_event_data, event_id="evt123", client=mock_client
        )


@patch("app.utils.handler_utils.forward_to_pull_request_lambda")
def test_process_async_slack_event_pull_request_with_mention(
    mock_forward_to_pull_request_lambda: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test successful async event processing"""
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_event

    # perform operation
    slack_event_data = {
        "text": "<@U123> pr: 123 test question",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
    }
    with patch("app.slack.slack_events.process_feedback_event") as mock_process_feedback_event, patch(
        "app.slack.slack_events.process_slack_message"
    ) as mock_process_slack_message:
        process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)
        mock_forward_to_pull_request_lambda.assert_called_once_with(
            body={},
            pull_request_id="123",
            event=slack_event_data,
            event_id="evt123",
            store_pull_request_id=True,
            type="event",
        )
        mock_process_feedback_event.assert_not_called()
        mock_process_slack_message.assert_not_called()


@patch("app.utils.handler_utils.forward_to_pull_request_lambda")
def test_process_async_slack_event_pull_request_with_no_mention(
    mock_forward_to_pull_request_lambda: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test successful async event processing"""
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_event

    # perform operation
    slack_event_data = {
        "text": "pr: 123 test question",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
    }
    with patch("app.slack.slack_events.process_feedback_event") as mock_process_feedback_event, patch(
        "app.slack.slack_events.process_slack_message"
    ) as mock_process_slack_message:
        process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)
        mock_forward_to_pull_request_lambda.assert_called_once_with(
            body={},
            pull_request_id="123",
            event=slack_event_data,
            event_id="evt123",
            store_pull_request_id=True,
            type="event",
        )
        mock_process_feedback_event.assert_not_called()
        mock_process_slack_message.assert_not_called()


def test_process_slack_message_empty_query(mock_get_parameter: Mock, mock_env: Mock):
    """Test async event processing with empty query"""
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {
        "text": "<@U123>",  # Only mention, no actual query
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
    }
    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    mock_client.chat_postMessage.assert_called_once_with(
        channel="C789",
        text="Hi there! Please ask me a question and I'll help you find information from our knowledge base.",
        thread_ts="1234567890.123",
    )


@patch("app.services.dynamo.get_state_information")
@patch("app.services.ai_processor.process_ai_query")
@patch("app.slack.slack_events.get_conversation_session")
def test_process_slack_message_with_thread_ts(
    mock_get_session: Mock,
    mock_process_ai_query: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test async event processing with existing thread_ts"""
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "session-123",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}},
    }
    mock_get_session.return_value = None  # No existing session

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
        from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {
        "text": "<@U123> test question",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
        "thread_ts": "1234567888.111",  # Existing thread
    }
    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    # Should be called at least once with the correct thread_ts
    assert mock_client.chat_postMessage.call_count >= 1
    first_call = mock_client.chat_postMessage.call_args_list[0]
    assert first_call[1]["thread_ts"] == "1234567888.111"
    assert first_call[1]["text"] == "Processing..."


@patch("app.services.dynamo.get_state_information")
@patch("app.services.ai_processor.process_ai_query")
@patch("app.slack.slack_events.get_conversation_session")
def test_regex_text_processing(
    mock_get_session: Mock,
    mock_process_ai_query: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": ""}
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "session-123",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}},
    }
    mock_get_session.return_value = None  # No existing session

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {"text": "<@U123456> test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"}

    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    # Verify that the message was processed (process_ai_query was called)
    mock_process_ai_query.assert_called_once()
    # The actual regex processing happens inside the function
    assert mock_client.chat_postMessage.called


@patch("app.services.dynamo.get_state_information")
@patch("app.services.dynamo.store_state_information")
@patch("app.services.ai_processor.process_ai_query")
def test_process_slack_message_with_session_storage(
    mock_process_ai_query: Mock,
    mock_store_state_information: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test async event processing that stores a new session"""
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "ck": "thread#123",
        "session_id": "new-session-123",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}, "sessionId": "new-session-123"},
    }

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {
        "text": "test question",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
        "event_ts": "123",
    }

    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    # Verify session was stored - should be called twice (Q&A pair + session)
    assert mock_store_state_information.call_count >= 1


@patch("app.services.dynamo.get_state_information")
@patch("app.services.ai_processor.process_ai_query")
@patch("app.slack.slack_events.get_conversation_session")
def test_process_slack_message_chat_update_no_error(
    mock_get_session: Mock,
    mock_process_ai_query: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test process_async_slack_event with chat_update error"""
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.side_effect = Exception("Update failed")
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "session-123",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}},
    }
    mock_get_session.return_value = None  # No existing session

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {"text": "<@U123> test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"}
    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    # no assertions as we are just checking it does not throw an error


@patch("app.slack.slack_events.get_conversation_session")
@patch("app.slack.slack_events.get_conversation_session_data")
@patch("app.slack.slack_events.cleanup_previous_unfeedback_qa")
@patch("app.slack.slack_events.update_session_latest_message")
@patch("app.services.ai_processor.process_ai_query")
def test_process_slack_message_chat_update_cleanup(
    mock_process_ai_query: Mock,
    mock_update_session_latest_message: Mock,
    mock_cleanup_previous_unfeedback_qa: Mock,
    mock_get_conversation_session_data: Mock,
    mock_get_session: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test process_async_slack_event with chat_update error"""
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.side_effect = Exception("Update failed")
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "session-123",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}},
    }
    mock_get_conversation_session_data.return_value = {"session_id": "session-123"}
    mock_get_session.return_value = None  # No existing session
    mock_cleanup_previous_unfeedback_qa.return_value = {"test": "123"}

    # delete and import module to test
    from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {"text": "<@U123> test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"}
    with patch("app.slack.slack_events.get_conversation_session_data", mock_get_conversation_session_data):
        process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

        # assertions
        mock_cleanup_previous_unfeedback_qa.assert_called_once()
        mock_update_session_latest_message.assert_called_once()


@patch("app.services.dynamo.get_state_information")
@patch("app.services.ai_processor.process_ai_query")
@patch("app.slack.slack_events.get_conversation_session")
def test_process_slack_message_dm_context(
    mock_get_session: Mock,
    mock_process_ai_query: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test process_async_slack_event with DM context"""
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "123"}
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "new-session",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}, "sessionId": "new-session"},
    }
    mock_get_session.return_value = None

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_event

    # perform operation
    slack_event_data = {
        "text": "test question",
        "user": "U456",
        "channel": "D789",
        "ts": "123",
        "channel_type": "im",  # DM context
    }
    process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    # no assertions as we are just checking it does not throw an error


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_no_previous_message(
    mock_delete_state_information: Mock,
):
    """Test cleanup skipped when no previous message exists"""
    conversation_key = "conv-123"
    current_message_ts = "1234567890.124"
    session_data = {}

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    # perform operation
    cleanup_previous_unfeedback_qa(conversation_key, current_message_ts, session_data)

    # assertions
    mock_delete_state_information.assert_not_called()


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_same_message(
    mock_delete_state_information: Mock,
):
    """Test cleanup skipped when previous message is same as current"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    conversation_key = "conv-123"
    current_message_ts = "1234567890.123"
    session_data = {"latest_message_ts": "1234567890.123"}

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    # perform operation
    cleanup_previous_unfeedback_qa(conversation_key, current_message_ts, session_data)

    # assertions
    mock_delete_state_information.assert_not_called()


def test_create_response_body_creates_body_with_markdown_formatting(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    # perform operation
    response = _create_response_body(
        response_text="**Bold**, __italics__, and `code`.",
    )

    # assertions
    assert len(response) > 0
    assert response[0]["type"] == "section"

    response_value = response[0]["text"]["text"]

    assert "*Bold*, _italics_, and `code`." in response_value


def test_create_response_body_creates_body_with_lists(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    dirty_input = "Header text - Standard Dash -No Space Dash • Standard Bullet  -NoSpace-NoSpace"

    # perform operation
    response = _create_response_body(
        response_text=dirty_input,
    )

    # assertions
    assert len(response) > 0
    assert response[0]["type"] == "section"

    response_value = response[0]["text"]["text"]

    expected_output = "Header text\n- Standard Dash\n- No Space Dash\n- Standard Bullet\n- NoSpace-NoSpace"
    assert expected_output in response_value


def test_create_response_body_creates_body_without_encoding_errors(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    # perform operation
    response = _create_response_body(
        response_text="» Tabbing Issue. â¢ Bullet point issue.",
    )

    # assertions
    assert len(response) > 0
    assert response[0]["type"] == "section"

    response_value = response[0]["text"]["text"]

    assert "Tabbing Issue.\n- Bullet point issue." in response_value
