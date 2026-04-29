import sys
import pytest
from unittest.mock import ANY, Mock, patch, MagicMock


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
        citations=[],
        feedback_data={},
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

    dirty_input = "Header text - Standard Dash -No Space Dash • Standard Bullet  -DoubleSpace-NoSpace"

    # perform operation
    response = _create_response_body(
        citations=[],
        feedback_data={},
        response_text=dirty_input,
    )

    # assertions
    assert len(response) > 0
    assert response[0]["type"] == "section"

    response_value = response[0]["text"]["text"]

    expected_output = "Header text - Standard Dash -No Space Dash - Standard Bullet  -DoubleSpace-NoSpace"
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
        citations=[],
        feedback_data={},
        response_text="» Tabbing Issue. â¢ Bullet point issue.",
    )

    # assertions
    assert len(response) > 0
    assert response[0]["type"] == "section"

    response_value = response[0]["text"]["text"]

    assert "Tabbing Issue. - Bullet point issue." in response_value


# ================================================================
# Tests for _create_citation
# ================================================================


def test_create_citation_high_relevance_score(mock_get_parameter: Mock, mock_env: Mock):
    """Test citation creation with high relevance score"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_citation

    citation = {
        "source_number": "1",
        "title": "Test Document",
        "excerpt": "This is a test excerpt",
        "relevance_score": "0.95",
    }
    feedback_data = {"ck": "conv-123", "ch": "C789"}
    response_text = "Response with [cit_1] citation"

    result = _create_citation(citation, feedback_data, response_text)

    assert len(result["action_buttons"]) == 1
    button = result["action_buttons"][0]
    assert button["type"] == "button"
    assert button["text"]["text"] == "[1] Test Document"
    assert button["action_id"] == "cite_1"
    assert result["response_text"] == "Response with [1] citation"


def test_create_citation_low_relevance_score(mock_get_parameter: Mock, mock_env: Mock):
    """Test citation is skipped when relevance score is low"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_citation

    citation = {
        "source_number": "2",
        "title": "Low Relevance Doc",
        "excerpt": "This is low relevance",
        "relevance_score": "0.5",  # Below 0.6 threshold
    }
    feedback_data = {"ck": "conv-123"}
    response_text = "Response with [cit_2]"

    result = _create_citation(citation, feedback_data, response_text)

    assert len(result["action_buttons"]) == 0
    assert result["response_text"] == "Response with [cit_2]"


def test_create_citation_missing_excerpt(mock_get_parameter: Mock, mock_env: Mock):
    """Test citation with missing excerpt uses default message"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_citation

    citation = {
        "source_number": "3",
        "title": "Document Without Excerpt",
        "relevance_score": "0.9",
    }
    feedback_data = {"ck": "conv-123"}
    response_text = "Response text"

    result = _create_citation(citation, feedback_data, response_text)

    assert len(result["action_buttons"]) == 1
    import json

    button_data = json.loads(result["action_buttons"][0]["value"])
    assert button_data["body"] == "No document excerpt available."


def test_create_citation_missing_title_uses_filename(mock_get_parameter: Mock, mock_env: Mock):
    """Test citation uses filename when title is missing"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_citation

    citation = {
        "source_number": "4",
        "filename": "document.pdf",
        "excerpt": "Some content",
        "relevance_score": "0.85",
    }
    feedback_data = {"ck": "conv-123"}
    response_text = "Response text"

    result = _create_citation(citation, feedback_data, response_text)

    assert len(result["action_buttons"]) == 1
    assert result["action_buttons"][0]["text"]["text"] == "[4] document.pdf"


def test_create_citation_fallback_source_when_missing(mock_get_parameter: Mock, mock_env: Mock):
    """Test citation uses 'Source' when both title and filename are missing"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_citation

    citation = {
        "source_number": "5",
        "excerpt": "Some content",
        "relevance_score": "0.9",
    }
    feedback_data = {"ck": "conv-123"}
    response_text = "Response text"

    result = _create_citation(citation, feedback_data, response_text)

    assert len(result["action_buttons"]) == 1
    assert result["action_buttons"][0]["text"]["text"] == "[5] Source"


def test_create_citation_button_text_truncation(mock_get_parameter: Mock, mock_env: Mock):
    """Test citation button text is truncated when exceeds 75 characters"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_citation

    long_title = "A" * 80  # Title longer than 75 chars
    citation = {
        "source_number": "6",
        "title": long_title,
        "excerpt": "Some content",
        "relevance_score": "0.9",
    }
    feedback_data = {"ck": "conv-123"}
    response_text = "Response text"

    result = _create_citation(citation, feedback_data, response_text)

    button_text = result["action_buttons"][0]["text"]["text"]
    assert len(button_text) <= 77  # "[X] " + 70 chars + "..."
    assert button_text.endswith("...")


def test_create_citation_removes_newlines_from_source_number(mock_get_parameter: Mock, mock_env: Mock):
    """Test citation removes newlines from source number"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_citation

    citation = {
        "source_number": "7\n\n",
        "title": "Test",
        "excerpt": "Content",
        "relevance_score": "0.9",
    }
    feedback_data = {"ck": "conv-123"}
    response_text = "Response with [cit_7]"

    result = _create_citation(citation, feedback_data, response_text)

    assert result["response_text"] == "Response with [7]"
    assert result["action_buttons"][0]["action_id"] == "cite_7"


def test_create_citation_zero_relevance_score(mock_get_parameter: Mock, mock_env: Mock):
    """Test citation with zero relevance score is skipped"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_citation

    citation = {
        "source_number": "8",
        "title": "No Relevance",
        "excerpt": "Content",
        "relevance_score": "0",
    }
    feedback_data = {"ck": "conv-123"}
    response_text = "Response text"

    result = _create_citation(citation, feedback_data, response_text)

    assert len(result["action_buttons"]) == 0


# ================================================================
# Tests for convert_markdown_to_slack
# ================================================================


def test_convert_markdown_to_slack_bold_formatting(mock_get_parameter: Mock, mock_env: Mock):
    """Test conversion of markdown bold to Slack formatting"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    markdown_text = "This is **bold text** in markdown"
    result = convert_markdown_to_slack(markdown_text)

    assert "*bold text*" in result


def test_convert_markdown_to_slack_italic_formatting(mock_get_parameter: Mock, mock_env: Mock):
    """Test conversion of markdown italics to Slack formatting"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    markdown_text = "This is __italic text__ in markdown"
    result = convert_markdown_to_slack(markdown_text)

    assert "_italic text_" in result


def test_convert_markdown_to_slack_links(mock_get_parameter: Mock, mock_env: Mock):
    """Test conversion of markdown links to Slack formatting"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    markdown_text = "Check out [this link](https://example.com)"
    result = convert_markdown_to_slack(markdown_text)

    assert "<https://example.com|this link>" in result


def test_convert_markdown_to_slack_encoding_issues_arrow(mock_get_parameter: Mock, mock_env: Mock):
    """Test conversion removes arrow encoding issues"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    text_with_encoding = "» Tab issue"
    result = convert_markdown_to_slack(text_with_encoding)

    assert "»" not in result
    assert "Tab issue" in result


def test_convert_markdown_to_slack_encoding_issues_bullet(mock_get_parameter: Mock, mock_env: Mock):
    """Test conversion fixes bullet point encoding issues"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    text_with_encoding = "â¢ Bullet point"
    result = convert_markdown_to_slack(text_with_encoding)

    assert "â¢" not in result
    assert "- Bullet point" in result


def test_convert_markdown_to_slack_empty_string(mock_get_parameter: Mock, mock_env: Mock):
    """Test conversion of empty string"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    result = convert_markdown_to_slack("")

    assert result == ""


def test_convert_markdown_to_slack_none_string(mock_get_parameter: Mock, mock_env: Mock):
    """Test conversion of None string"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    result = convert_markdown_to_slack(None)

    assert result == ""


def test_convert_markdown_to_slack_combined_formatting(mock_get_parameter: Mock, mock_env: Mock):
    """Test conversion with multiple formatting types"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    text = "Check **bold** and __italic__ with [link](https://test.com)"
    result = convert_markdown_to_slack(text)

    assert "*bold*" in result
    assert "_italic_" in result
    assert "<https://test.com|link>" in result


def test_convert_markdown_to_slack_link_with_newlines_no_space(mock_get_parameter: Mock, mock_env: Mock):
    """Test link conversion removes newlines from link text"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    text = "Check [link\ntext](https://example.com)"
    result = convert_markdown_to_slack(text)

    assert "<https://example.com|link text>" in result


def test_convert_markdown_to_slack_link_with_newlines_with_space(mock_get_parameter: Mock, mock_env: Mock):
    """Test link conversion removes newlines from link text"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    text = "Check [link \n text](https://example.com)"
    result = convert_markdown_to_slack(text)

    assert "<https://example.com|link   text>" in result


def test_convert_markdown_to_slack_link_with_newlines_with_dash(mock_get_parameter: Mock, mock_env: Mock):
    """Test link conversion removes newlines from link text"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    text = "Check [link-text](https://example.com)"
    result = convert_markdown_to_slack(text)

    assert "<https://example.com|link-text>" in result


def test_convert_markdown_to_slack_link_with_newlines_with_dash_and_space(mock_get_parameter: Mock, mock_env: Mock):
    """Test link conversion removes newlines from link text"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    text = "Check [link - text](https://example.com)"
    result = convert_markdown_to_slack(text)

    assert "<https://example.com|link - text>" in result


def test_convert_markdown_to_slack_whitespace_stripped(mock_get_parameter: Mock, mock_env: Mock):
    """Test conversion strips leading/trailing whitespace"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    text = "  Some text with spaces  "
    result = convert_markdown_to_slack(text)

    assert result == "Some text with spaces"


def test_convert_markdown_to_slack_multiple_encoding_issues(mock_get_parameter: Mock, mock_env: Mock):
    """Test conversion handles multiple encoding issues"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import convert_markdown_to_slack

    text = "» Tab issue. â¢ Bullet point â¢ another bullet"
    result = convert_markdown_to_slack(text)

    assert "»" not in result
    assert "â¢" not in result
    assert "- Bullet point" in result
    assert "- another bullet" in result


# ================================================================
# Tests for deleted messages after message edit
# ================================================================


def test_handle_modified_messages_last_user_message_in_chain():
    """If the message is the last in the chain, delete reply and continue"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _handle_modified_messages

    mock_client = Mock()
    # Mock conversation history: Original user message + 2 Bot replies
    mock_client.conversations_replies.return_value = {
        "messages": [
            {"ts": "100.000", "user": "U123"},
            {"ts": "101.000", "user": "BOT_ID"},
            {"ts": "102.000", "user": "BOT_ID"},
        ]
    }

    result = _handle_modified_messages(
        client=mock_client,
        channel="C123",
        thread_ts="100.000",
        original_ts="100.000",
        edited_event={"ts": "105.000"},
        event_id="evt123",
        user_id="U123",
    )

    # Assertions
    assert result is True
    assert mock_client.chat_delete.call_count == 2
    mock_client.chat_postEphemeral.assert_not_called()


def test_handle_modified_messages_not_last_user_message_in_chain():
    """If the message is not the last user message, post ephemeral msg and return False"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _handle_modified_messages

    mock_client = Mock()
    # Mock conversation history: Original message + Bot reply + Another user message (user replied again)
    mock_client.conversations_replies.return_value = {
        "messages": [
            {"ts": "100.000", "user": "U123"},
            {"ts": "101.000", "user": "BOT_ID"},
            {"ts": "102.000", "user": "U123"},
        ]
    }

    result = _handle_modified_messages(
        client=mock_client,
        channel="C123",
        thread_ts="100.000",
        original_ts="100.000",
        edited_event={"ts": "105.000"},
        event_id="evt123",
        user_id="U123",
    )

    # Assertions
    assert result is False
    mock_client.chat_delete.assert_not_called()
    mock_client.chat_postEphemeral.assert_called_once_with(
        channel="C123",
        user="U123",
        thread_ts="100.000",
        text="It looks like the conversation has diverged, please start a new conversation",
    )


def test_process_slack_message_halts_on_false_modified_handler(
    mock_env: Mock,
    mock_get_parameter: Mock,
):
    """Test that process_slack_message stops processing if the edit is rejected (not last in chain)"""
    mock_client = Mock()

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    event = {
        "text": "updated question",
        "user": "U123",
        "channel": "C123",
        "ts": "123.123",
        "edited": {"ts": "456.789"},
        "thread_ts": "123.123",
    }

    # Patch dynamically inside the test body to avoid the module reload issue
    with patch("app.slack.slack_events._handle_modified_messages") as mock_handle_modified_messages, patch(
        "app.slack.slack_events.get_conversation_session_data"
    ) as mock_get_conversation_session_data:

        mock_handle_modified_messages.return_value = False

        process_slack_message(event=event, event_id="evt123", client=mock_client)

        # Assertions
        mock_handle_modified_messages.assert_called_once_with(
            client=mock_client,
            channel="C123",
            thread_ts="123.123",
            original_ts="123.123",
            edited_event={"ts": "456.789"},
            event_id="evt123",
            user_id="U123",
        )

        # Ensure it stopped execution and didn't try to fetch conversation memory / call Bedrock
        mock_get_conversation_session_data.assert_not_called()
        mock_client.chat_postMessage.assert_not_called()


def test_process_slack_message_continues_on_true_modified_handler(mock_env: Mock, mock_get_parameter: Mock):
    """Test that process_slack_message completes if the edit is accepted"""
    mock_client = Mock()
    # Mock the response for the "Processing..." message
    mock_client.chat_postMessage.return_value = {"ts": "999.999"}

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    event = {
        "text": "updated question",
        "user": "U123",
        "channel": "C123",
        "ts": "123.123",
        "edited": {"ts": "456.789"},
        "thread_ts": "123.123",
        "event_ts": "123.123",  # Required by log_query_stats
        "channel_type": "channel",
    }

    # Patch dynamically inside the test body to avoid the module reload issue wiping the mocks
    with patch("app.slack.slack_events._handle_modified_messages") as mock_handle_modified_messages, patch(
        "app.slack.slack_events.get_conversation_session_data"
    ) as mock_get_conversation_session_data, patch(
        "app.slack.slack_events.process_formatted_bedrock_query"
    ) as mock_process_formatted_bedrock_query, patch(
        "app.slack.slack_events._handle_session_management"
    ), patch(
        "app.slack.slack_events.store_qa_pair"
    ), patch(
        "app.slack.slack_events.log_query_stats"
    ):

        mock_handle_modified_messages.return_value = True

        mock_get_conversation_session_data.return_value = {"session_id": "session-123"}
        mock_process_formatted_bedrock_query.return_value = ({"sessionId": "session-123"}, "AI response", [])

        process_slack_message(event=event, event_id="evt123", client=mock_client)

        mock_handle_modified_messages.assert_called_once()
        mock_get_conversation_session_data.assert_called_once()

        # Check it posted the "Processing..." message
        mock_client.chat_postMessage.assert_called_once_with(channel="C123", text="Processing...", thread_ts="123.123")

        mock_process_formatted_bedrock_query.assert_called_once()

        # Check it updated the slack message
        mock_client.chat_update.assert_called_once_with(
            channel="C123",
            ts="999.999",  # This matches the mock_client.chat_postMessage.return_value
            text="AI response",
            blocks=ANY,
        )


def test_notify_diverged_conversation_success():
    """Test successful posting of the ephemeral warning message."""
    mock_client = Mock()

    from app.slack.slack_events import _notify_diverged_conversation

    _notify_diverged_conversation(mock_client, "C123", "U123", "100.000", "evt123")

    mock_client.chat_postEphemeral.assert_called_once_with(
        channel="C123",
        user="U123",
        thread_ts="100.000",
        text="It looks like the conversation has diverged, please start a new conversation",
    )


@patch("app.slack.slack_events.logger")
def test_notify_diverged_conversation_exception(mock_logger):
    """Test that exceptions during ephemeral posting are caught and logged."""
    mock_client = Mock()
    mock_client.chat_postEphemeral.side_effect = Exception("API error")

    from app.slack.slack_events import _notify_diverged_conversation

    # Should not raise an exception
    _notify_diverged_conversation(mock_client, "C123", "U123", "100.000", "evt123")

    mock_client.chat_postEphemeral.assert_called_once()
    mock_logger.error.assert_called_once()
    assert "Couldn't post ephemeral message: API error" in mock_logger.error.call_args[0][0]
