import sys
import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def mock_logger():
    return MagicMock()


@patch("app.utils.handler_utils.forward_to_pull_request_lambda")
def test_process_slack_command(
    mock_forward_to_pull_request_lambda: Mock,
):
    """Test successful command processing"""
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_command

    # perform operation
    slack_command_data = {
        "text": "",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
        "command": "/test",
    }
    with patch("app.slack.slack_events.process_command_test_response") as mock_process_command_test_response, patch(
        "app.slack.slack_events.process_slack_message"
    ) as mock_process_slack_message, patch(
        "app.slack.slack_events.process_async_slack_event"
    ) as mock_process_async_slack_event:
        process_async_slack_command(command=slack_command_data, client=mock_client)
        mock_forward_to_pull_request_lambda.assert_not_called()
        mock_process_command_test_response.assert_called_once_with(
            command={**slack_command_data},
            client=mock_client,
        )
        mock_process_slack_message.assert_not_called()
        mock_process_async_slack_event.assert_not_called()


@patch("app.services.ai_processor.process_ai_query")
def test_process_slack_command_test_questions_default(
    mock_process_ai_query: Mock,
):
    """Test successful command processing"""
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_command

    # perform operation
    slack_command_data = {
        "text": "",
        "user": "U456",
        "channel_id": "C789",
        "ts": "1234567890.123",
        "command": "/test",
    }

    mock_response = MagicMock()
    mock_response.data = {}
    mock_response.get.side_effect = lambda k: {"thread_ts": "1234567890.123456", "channel": "C12345678"}.get(k)
    mock_client.chat_postMessage.return_value = mock_response

    mock_process_ai_query.return_value = {"text": "ai response", "session_id": None, "citations": [], "kb_response": {}}

    # perform operation
    process_async_slack_command(command=slack_command_data, client=mock_client)

    # assertions
    mock_client.chat_postMessage.assert_called()
    assert mock_client.chat_postMessage.call_count == 21


@patch("app.services.ai_processor.process_ai_query")
def test_process_slack_command_test_questions_single_question(
    mock_process_ai_query: Mock,
):
    """Test successful command processing"""
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_command

    # perform operation
    slack_command_data = {
        "text": "q2",
        "user": "U456",
        "channel_id": "C789",
        "ts": "1234567890.123",
        "command": "/test",
    }

    mock_response = MagicMock()
    mock_response.data = {}
    mock_response.get.side_effect = lambda k: {"thread_ts": "1234567890.123456", "channel": "C12345678"}.get(k)
    mock_client.chat_postMessage.return_value = mock_response

    mock_process_ai_query.return_value = {"text": "ai response", "session_id": None, "citations": [], "kb_response": {}}

    # perform operation
    process_async_slack_command(command=slack_command_data, client=mock_client)

    # assertions
    mock_client.chat_postMessage.assert_called()
    mock_client.chat_postMessage.assert_called_once()


@patch("app.services.ai_processor.process_ai_query")
def test_process_slack_command_test_questions_two_questions(
    mock_process_ai_query: Mock,
):
    """Test successful command processing"""
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_command

    # perform operation
    slack_command_data = {
        "text": "q2-3",
        "user": "U456",
        "channel_id": "C789",
        "ts": "1234567890.123",
        "command": "/test",
    }

    mock_client.chat_postMessage.return_value = {}

    mock_process_ai_query.return_value = {"text": "ai response", "session_id": None, "citations": [], "kb_response": {}}

    # perform operation
    process_async_slack_command(command=slack_command_data, client=mock_client)

    # assertions
    mock_client.chat_postMessage.assert_called()
    assert mock_client.chat_postMessage.call_count == 2


@patch("app.services.ai_processor.process_ai_query")
def test_process_slack_command_test_questions_too_many_questions_error(
    mock_process_ai_query: Mock,
    mock_logger: Mock,
):
    """Test successful command processing"""
    # set up mocks
    with patch("app.core.config.get_logger", return_value=mock_logger):
        mock_client = Mock()

        # delete and import module to test
        if "app.slack.slack_events" in sys.modules:
            del sys.modules["app.slack.slack_events"]
        from app.slack.slack_events import process_async_slack_command

        # perform operation
        slack_command_data = {
            "text": "q0-100",
            "user": "U456",
            "channel_id": "C789",
            "ts": "1234567890.123",
            "command": "/test",
        }

        mock_client.chat_postMessage.return_value = {}

        mock_process_ai_query.return_value = {
            "text": "ai response",
            "session_id": None,
            "citations": [],
            "kb_response": {},
        }

        # with pytest.raises(ValueError, match="'end' must be less than 21"):
        # perform operation
        process_async_slack_command(command=slack_command_data, client=mock_client)

        # assertions
        mock_client.chat_postMessage.asset_not_called()

        mock_logger.error.assert_called_once()


@patch("app.services.ai_processor.process_ai_query")
def test_process_slack_command_test_help(
    mock_process_ai_query: Mock,
):
    """Test successful command processing"""
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_command

    # perform operation
    slack_command_data = {
        "text": "help",
        "user": "U456",
        "channel_id": "C789",
        "ts": "1234567890.123",
        "command": "/test",
    }

    mock_response = MagicMock()
    mock_response.data = {}
    mock_client.chat_postMessage.return_value = mock_response

    mock_process_ai_query.return_value = {"text": "ai response", "session_id": None, "citations": [], "kb_response": {}}

    # perform operation
    process_async_slack_command(command=slack_command_data, client=mock_client)

    # assertions
    mock_client.chat_meMessage.assert_called_once()
    mock_client.chat_postMessage.assert_not_called()
