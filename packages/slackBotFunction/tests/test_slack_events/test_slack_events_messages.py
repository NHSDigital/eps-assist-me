import pytest
from unittest.mock import ANY, Mock, patch, MagicMock
from app.core.config import bot_messages


@pytest.fixture
def mock_logger():
    return MagicMock()


@patch("app.slack.slack_events.forward_to_pull_request_lambda")
def test_process_async_slack_event_normal_message(
    mock_forward_events: Mock,
):
    """Test successful async event processing"""
    mock_client = Mock()

    from app.slack.slack_events import process_async_slack_event

    slack_event_data = {
        "text": "<@U123> test question",
        "user": "U456",
        "channel": "D789",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "channel_type": "im",
    }
    with patch("app.slack.slack_events.process_feedback_event") as mock_process_feedback_event, patch(
        "app.slack.slack_events.process_slack_message"
    ) as mock_process_slack_message:
        process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)
        mock_forward_events.assert_not_called()
        mock_process_feedback_event.assert_not_called()
        mock_process_slack_message.assert_called_once_with(
            event=slack_event_data, event_id="evt123", client=mock_client
        )


@patch("app.slack.slack_events.forward_to_pull_request_lambda")
def test_process_async_slack_event_pull_request_with_mention(
    mock_forward_events: Mock,
):
    """Test successful async event processing"""
    mock_client = Mock()

    from app.slack.slack_events import process_async_slack_event

    slack_event_data = {
        "text": "<@U123> pr: 123 test question",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "channel_type": "channel",
    }
    with patch("app.slack.slack_events.process_feedback_event") as mock_process_feedback_event, patch(
        "app.slack.slack_events.process_slack_message"
    ) as mock_process_slack_message:
        process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)
        mock_forward_events.assert_called_once_with(
            body={},
            pull_request_id="123",
            event=slack_event_data,
            event_id="evt123",
            store_pull_request_id=True,
            type="event",
        )
        mock_process_feedback_event.assert_not_called()
        mock_process_slack_message.assert_not_called()


@patch("app.slack.slack_events.forward_to_pull_request_lambda")
def test_process_async_slack_event_pull_request_with_no_mention(
    mock_forward_events: Mock,
):
    """Test successful async event processing"""
    mock_client = Mock()

    from app.slack.slack_events import process_async_slack_event

    slack_event_data = {
        "text": "pr: 123 test question",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "channel_type": "channel",
    }
    with patch("app.slack.slack_events.process_feedback_event") as mock_process_feedback_event, patch(
        "app.slack.slack_events.process_slack_message"
    ) as mock_process_slack_message:
        process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)
        mock_forward_events.assert_called_once_with(
            body={},
            pull_request_id="123",
            event=slack_event_data,
            event_id="evt123",
            store_pull_request_id=True,
            type="event",
        )
        mock_process_feedback_event.assert_not_called()
        mock_process_slack_message.assert_not_called()


@patch("app.slack.slack_events.is_duplicate_event", return_value=False)
def test_process_slack_message_empty_query(mock_is_duplicate_event: Mock):
    """Test async event processing with empty query"""
    mock_client = Mock()

    from app.slack.slack_events import process_slack_message

    slack_event_data = {
        "text": "<@U123>",
        "user": "U456",
        "channel": "D789",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "channel_type": "im",
    }
    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    mock_client.chat_postMessage.assert_called_once_with(
        channel="D789", text=bot_messages.EMPTY_QUERY, thread_ts="1234567890.123"
    )


@patch("app.slack.slack_events.process_ai_query")
@patch("app.slack.slack_events.get_conversation_session_data", return_value={})
@patch("app.slack.slack_events.is_duplicate_event", return_value=False)
def test_process_slack_message_with_thread_ts(
    mock_is_duplicate_event: Mock, mock_get_session: Mock, mock_process_ai_query: Mock
):
    """Test async event processing with existing thread_ts"""
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "session-123",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}},
    }

    from app.slack.slack_events import process_slack_message

    slack_event_data = {
        "text": "<@U123> test question",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "channel_type": "channel",
        "thread_ts": "1234567888.111",
    }
    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    assert mock_client.chat_postMessage.call_count >= 1
    first_call = mock_client.chat_postMessage.call_args_list[0]
    assert first_call[1]["thread_ts"] == "1234567888.111"
    assert first_call[1]["text"] == "Processing..."


@patch("app.slack.slack_events.process_ai_query")
@patch("app.slack.slack_events.get_conversation_session_data", return_value={})
@patch("app.slack.slack_events.is_duplicate_event", return_value=False)
def test_regex_text_processing(mock_is_duplicate_event: Mock, mock_get_session: Mock, mock_process_ai_query: Mock):
    """Test regex text processing functionality within process_async_slack_event"""
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "123"}
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "session-123",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}},
    }

    from app.slack.slack_events import process_slack_message

    slack_event_data = {
        "text": "<@U123456> test question",
        "user": "U456",
        "channel": "D789",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "channel_type": "im",
    }

    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    mock_process_ai_query.assert_called_once()
    assert mock_client.chat_postMessage.called


@patch("app.slack.slack_events.store_state_information")
@patch("app.slack.slack_events.process_ai_query")
@patch("app.slack.slack_events.is_duplicate_event", return_value=False)
def test_process_slack_message_with_session_storage(
    mock_is_duplicate_event: Mock,
    mock_process_ai_query: Mock,
    mock_store_state_information: Mock,
):
    """Test async event processing that stores a new session"""
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

    from app.slack.slack_events import process_slack_message

    slack_event_data = {
        "text": "test question",
        "user": "U456",
        "channel": "D789",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "channel_type": "im",
    }

    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    assert mock_store_state_information.call_count >= 1


@patch("app.slack.slack_events.process_ai_query")
@patch("app.slack.slack_events.get_conversation_session_data", return_value={})
@patch("app.slack.slack_events.is_duplicate_event", return_value=False)
def test_process_slack_message_chat_update_no_error(
    mock_is_duplicate_event: Mock, mock_get_session: Mock, mock_process_ai_query: Mock
):
    """Test process_async_slack_event with chat_update error"""
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.side_effect = Exception("Update failed")
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "session-123",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}},
    }

    from app.slack.slack_events import process_slack_message

    slack_event_data = {
        "text": "<@U123> test question",
        "user": "U456",
        "channel": "D789",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "channel_type": "im",
    }
    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)


@patch("app.slack.slack_events.update_state_information")
@patch("app.slack.slack_events.get_conversation_session_data", return_value={"session_id": "session-123"})
@patch("app.slack.slack_events.process_ai_query")
@patch("app.slack.slack_events.is_duplicate_event", return_value=False)
def test_process_slack_message_chat_update_cleanup(
    mock_is_duplicate_event: Mock,
    mock_process_ai_query: Mock,
    mock_get_conversation_session_data: Mock,
    mock_update_state_information: Mock,
):
    """Test process_async_slack_event with chat_update error"""
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.side_effect = Exception("Update failed")
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "session-123",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}},
    }

    from app.slack.slack_events import process_slack_message

    slack_event_data = {
        "text": "<@U123> test question",
        "user": "U456",
        "channel": "D789",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "channel_type": "im",
    }
    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    mock_update_state_information.assert_called_once()


@patch("app.slack.slack_events.process_ai_query")
@patch("app.slack.slack_events.get_conversation_session_data", return_value={})
@patch("app.slack.slack_events.is_duplicate_event", return_value=False)
def test_process_slack_message_dm_context(
    mock_is_duplicate_event: Mock, mock_get_session: Mock, mock_process_ai_query: Mock
):
    """Test process_async_slack_event with DM context"""
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "123"}
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "new-session",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}, "sessionId": "new-session"},
    }

    from app.slack.slack_events import process_async_slack_event

    slack_event_data = {
        "text": "test question",
        "user": "U456",
        "channel": "D789",
        "ts": "123",
        "event_ts": "123",
        "channel_type": "im",
    }
    with patch("app.slack.slack_events.process_slack_message") as mock_process_slack_message:
        process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)
        mock_process_slack_message.assert_called_once()


@patch("app.slack.slack_events.delete_state_information")
def test_cleanup_previous_unfeedback_qa_no_previous_message(
    mock_delete_state_information: Mock,
):
    """Test cleanup skipped when no previous message exists"""
    conversation_key = "conv-123"
    current_message_ts = "1234567890.124"
    session_data = {}

    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    cleanup_previous_unfeedback_qa(conversation_key, current_message_ts, session_data)
    mock_delete_state_information.assert_not_called()


@patch("app.slack.slack_events.delete_state_information")
def test_cleanup_previous_unfeedback_qa_same_message(
    mock_delete_state_information: Mock,
):
    """Test cleanup skipped when previous message is same as current"""
    conversation_key = "conv-123"
    current_message_ts = "1234567890.123"
    session_data = {"latest_message_ts": "1234567890.123"}

    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    cleanup_previous_unfeedback_qa(conversation_key, current_message_ts, session_data)
    mock_delete_state_information.assert_not_called()


def test_create_response_body_creates_body_with_markdown_formatting():
    """Test regex text processing functionality within process_async_slack_event"""
    from app.slack.slack_events import _create_response_body

    response = _create_response_body(
        citations=[],
        feedback_data={},
        response_text="**Bold**, __italics__, and `code`.",
    )

    assert len(response) > 0
    assert response[0]["type"] == "section"
    response_value = response[0]["text"]["text"]
    assert "*Bold*, _italics_, and `code`." in response_value


def test_create_response_body_creates_body_with_lists():
    """Test regex text processing functionality within process_async_slack_event"""
    from app.slack.slack_events import _create_response_body

    dirty_input = "Header text - Standard Dash -No Space Dash • Standard Bullet  -DoubleSpace-NoSpace"

    response = _create_response_body(
        citations=[],
        feedback_data={},
        response_text=dirty_input,
    )

    assert len(response) > 0
    assert response[0]["type"] == "section"
    response_value = response[0]["text"]["text"]
    expected_output = "Header text - Standard Dash -No Space Dash - Standard Bullet  -DoubleSpace-NoSpace"
    assert expected_output in response_value


def test_create_response_body_creates_body_without_encoding_errors():
    """Test regex text processing functionality within process_async_slack_event"""
    from app.slack.slack_events import _create_response_body

    response = _create_response_body(
        citations=[],
        feedback_data={},
        response_text="» Tabbing Issue. â¢ Bullet point issue.",
    )

    assert len(response) > 0
    assert response[0]["type"] == "section"
    response_value = response[0]["text"]["text"]
    assert "Tabbing Issue. - Bullet point issue." in response_value


# ================================================================
# Tests for _create_citation
# ================================================================


def test_create_citation_high_relevance_score():
    """Test citation creation with high relevance score"""
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


def test_create_citation_low_relevance_score():
    """Test citation is skipped when relevance score is low"""
    from app.slack.slack_events import _create_citation

    citation = {
        "source_number": "2",
        "title": "Low Relevance Doc",
        "excerpt": "This is low relevance",
        "relevance_score": "0.5",
    }
    feedback_data = {"ck": "conv-123"}
    response_text = "Response with [cit_2]"

    result = _create_citation(citation, feedback_data, response_text)

    assert len(result["action_buttons"]) == 0
    assert result["response_text"] == "Response with [cit_2]"


def test_create_citation_missing_excerpt():
    """Test citation with missing excerpt uses default message"""
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


def test_create_citation_missing_title_uses_filename():
    """Test citation uses filename when title is missing"""
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


def test_create_citation_fallback_source_when_missing():
    """Test citation uses 'Source' when both title and filename are missing"""
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


def test_create_citation_button_text_truncation():
    """Test citation button text is truncated when exceeds 75 characters"""
    from app.slack.slack_events import _create_citation

    long_title = "A" * 80
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
    assert len(button_text) <= 77
    assert button_text.endswith("...")


def test_create_citation_removes_newlines_from_source_number():
    """Test citation removes newlines from source number"""
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


def test_create_citation_zero_relevance_score():
    """Test citation with zero relevance score is skipped"""
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


def test_convert_markdown_to_slack_bold_formatting():
    """Test conversion of markdown bold to Slack formatting"""
    from app.slack.slack_events import convert_markdown_to_slack

    markdown_text = "This is **bold text** in markdown"
    result = convert_markdown_to_slack(markdown_text)
    assert "*bold text*" in result


def test_convert_markdown_to_slack_italic_formatting():
    """Test conversion of markdown italics to Slack formatting"""
    from app.slack.slack_events import convert_markdown_to_slack

    markdown_text = "This is __italic text__ in markdown"
    result = convert_markdown_to_slack(markdown_text)
    assert "_italic text_" in result


def test_convert_markdown_to_slack_links():
    """Test conversion of markdown links to Slack formatting"""
    from app.slack.slack_events import convert_markdown_to_slack

    markdown_text = "Check out [this link](https://example.com)"
    result = convert_markdown_to_slack(markdown_text)
    assert "<https://example.com|this link>" in result


def test_convert_markdown_to_slack_encoding_issues_arrow():
    """Test conversion removes arrow encoding issues"""
    from app.slack.slack_events import convert_markdown_to_slack

    text_with_encoding = "» Tab issue"
    result = convert_markdown_to_slack(text_with_encoding)

    assert "»" not in result
    assert "Tab issue" in result


def test_convert_markdown_to_slack_encoding_issues_bullet():
    """Test conversion fixes bullet point encoding issues"""
    from app.slack.slack_events import convert_markdown_to_slack

    text_with_encoding = "â¢ Bullet point"
    result = convert_markdown_to_slack(text_with_encoding)

    assert "â¢" not in result
    assert "- Bullet point" in result


def test_convert_markdown_to_slack_empty_string():
    """Test conversion of empty string"""
    from app.slack.slack_events import convert_markdown_to_slack

    result = convert_markdown_to_slack("")
    assert result == ""


def test_convert_markdown_to_slack_none_string():
    """Test conversion of None string"""
    from app.slack.slack_events import convert_markdown_to_slack

    result = convert_markdown_to_slack(None)
    assert result == ""


def test_convert_markdown_to_slack_combined_formatting():
    """Test conversion with multiple formatting types"""
    from app.slack.slack_events import convert_markdown_to_slack

    text = "Check **bold** and __italic__ with [link](https://test.com)"
    result = convert_markdown_to_slack(text)

    assert "*bold*" in result
    assert "_italic_" in result
    assert "<https://test.com|link>" in result


def test_convert_markdown_to_slack_link_with_newlines_no_space():
    """Test link conversion removes newlines from link text"""
    from app.slack.slack_events import convert_markdown_to_slack

    text = "Check [link\ntext](https://example.com)"
    result = convert_markdown_to_slack(text)
    assert "<https://example.com|link text>" in result


def test_convert_markdown_to_slack_link_with_newlines_with_space():
    """Test link conversion removes newlines from link text"""
    from app.slack.slack_events import convert_markdown_to_slack

    text = "Check [link \n text](https://example.com)"
    result = convert_markdown_to_slack(text)
    assert "<https://example.com|link   text>" in result


def test_convert_markdown_to_slack_link_with_newlines_with_dash():
    """Test link conversion removes newlines from link text"""
    from app.slack.slack_events import convert_markdown_to_slack

    text = "Check [link-text](https://example.com)"
    result = convert_markdown_to_slack(text)
    assert "<https://example.com|link-text>" in result


def test_convert_markdown_to_slack_link_with_newlines_with_dash_and_space():
    """Test link conversion removes newlines from link text"""
    from app.slack.slack_events import convert_markdown_to_slack

    text = "Check [link - text](https://example.com)"
    result = convert_markdown_to_slack(text)
    assert "<https://example.com|link - text>" in result


def test_convert_markdown_to_slack_whitespace_stripped():
    """Test conversion strips leading/trailing whitespace"""
    from app.slack.slack_events import convert_markdown_to_slack

    text = "  Some text with spaces  "
    result = convert_markdown_to_slack(text)
    assert result == "Some text with spaces"


def test_convert_markdown_to_slack_multiple_encoding_issues():
    """Test conversion handles multiple encoding issues"""
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
    

# ================================================================
# Tests for duplicate message handling
# ================================================================


@patch("app.slack.slack_events.get_conversation_session_data", return_value={})
@patch("app.slack.slack_events.process_formatted_bedrock_query")
@patch("app.slack.slack_events.is_duplicate_event", return_value=False)
def test_process_slack_message_handles_conflict_exception(
    mock_is_duplicate: Mock,
    mock_process_bedrock: Mock,
    mock_get_session: Mock,
    mock_env: Mock,
    mock_get_parameter: Mock,
):
    """
    GIVEN the bot has posted a 'Processing...' placeholder
    WHEN Bedrock throws a ConflictException due to a race condition on the session ID
    THEN the placeholder should be cleared/updated with a friendly error
    AND the bot does not stay stuck in 'Processing...'
    """
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "placeholder_ts_123"}

    from app.slack.slack_events import process_slack_message
    from botocore.exceptions import ClientError
    from app.core.config import bot_messages

    error_response = {"Error": {"Code": "ConflictException", "Message": "Session is currently being used"}}
    mock_process_bedrock.side_effect = ClientError(error_response, "RetrieveAndGenerate")

    event = {
        "text": "<@U123> test question",
        "user": "U456",
        "channel": "D789",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "channel_type": "im",
    }

    process_slack_message(event=event, event_id="evt123", client=mock_client)

    mock_client.chat_postMessage.assert_any_call(channel="D789", text="Processing...", thread_ts="1234567890.123")
    mock_client.chat_postMessage.assert_any_call(
        channel="D789", text=bot_messages.ERROR_RESPONSE, thread_ts="1234567890.123"
    )


def test_should_reply_to_message_rejects_raw_message_in_public_channel():
    """
    GIVEN the bot is installed in a public channel
    WHEN a user @mentions the bot, firing a duplicate 'message' event alongside 'app_mention'
    THEN the 'message' event should be dropped to prevent a ConflictException race condition
    """
    from app.utils.handler_utils import should_reply_to_message

    event = {"channel_type": "channel", "type": "message", "channel": "C123", "ts": "123"}
    result = should_reply_to_message(event)

    assert result is False


def test_should_reply_to_message_accepts_app_mention_in_public_channel():
    """
    GIVEN the bot is installed in a public channel
    WHEN a user @mentions the bot, firing the 'app_mention' event
    THEN the event should proceed normally without being blocked
    """
    from app.utils.handler_utils import should_reply_to_message

    event = {"channel_type": "channel", "type": "app_mention", "channel": "C123", "ts": "123"}
    result = should_reply_to_message(event)

    assert result is True


def test_should_reply_to_message_accepts_dm_message():
    """
    GIVEN the bot is installed
    WHEN a user DMs the bot with a prompt (which only fires a 'message' event)
    THEN the event should proceed normally without being blocked
    """
    from app.utils.handler_utils import should_reply_to_message

    event = {"channel_type": "im", "type": "message", "channel": "D123", "ts": "123"}
    result = should_reply_to_message(event)

    assert result is True


@patch("app.slack.slack_events.is_duplicate_event")
@patch("app.slack.slack_events.logger")
def test_process_slack_message_duplicate_msg_id(mock_logger: Mock, mock_is_duplicate_event: Mock):
    """Test that overlapping app_mention/message events are skipped"""
    from app.slack.slack_events import process_slack_message

    # Setup
    mock_client = Mock()
    mock_is_duplicate_event.return_value = True  # Simulate a duplicate event

    event = {
        "user": "U123",
        "channel": "C123",
        "event_ts": "1234567890.123",
        "ts": "1234567890.123",
        "text": "test question",
        "channel_type": "channel",
    }

    # Execute
    process_slack_message(event=event, event_id="evt123", client=mock_client)

    # Assertions
    mock_is_duplicate_event.assert_called_with("msg_C123_1234567890.123")
    mock_logger.info.assert_called_with("Skipping overlapping app_mention/message event: msg_C123_1234567890.123")
    mock_client.chat_postMessage.assert_not_called()  # Ensure it returns early


@patch("app.slack.slack_events.is_duplicate_event")
@patch("app.slack.slack_events.logger")
def test_process_slack_message_overlapping_event(mock_logger: Mock, mock_is_duplicate_event: Mock):
    """Test that overlapping app_mention/message events are skipped"""
    from app.slack.slack_events import process_slack_message

    mock_client = Mock()
    # Simulate that this message was already processed
    mock_is_duplicate_event.return_value = True

    event = {
        "user": "U123",
        "channel": "C123",
        "ts": "1234567890.123",
        "event_ts": "1234567890.123",
        "text": "test question",
        "channel_type": "channel",
    }

    process_slack_message(event=event, event_id="evt123", client=mock_client)

    # Assert the new logic from the PR is triggered
    mock_is_duplicate_event.assert_called_with("msg_C123_1234567890.123")
    mock_logger.info.assert_called_with("Skipping overlapping app_mention/message event: msg_C123_1234567890.123")

    # Ensure execution returns early before calling Bedrock or Slack
    mock_client.chat_postMessage.assert_not_called()
