import sys
import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def mock_logger():
    return MagicMock()


@patch("app.slack.slack_events.process_async_slack_command")
def test_process_slack_command_handler_succeeds(mock_process_async_slack_command: Mock):
    """Test successful command processing"""
    # set up mocks
    mock_client = Mock()

    slack_command_data = {
        "text": "",
        "user_id": "U456",
        "channel_id": "C789",
        "ts": "1234567890.123",
        "command": "/test",
    }

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import command_handler

    # perform operation
    command_handler(slack_command_data, slack_command_data, mock_client)

    # assertions
    mock_process_async_slack_command.assert_called_once()


@patch("boto3.client")
@patch("app.utils.handler_utils.extract_test_command_params")
@patch("app.utils.handler_utils.forward_to_pull_request_lambda")
def test_process_slack_command_handler_forwards_pr(
    mock_forward_to_pull_request_lambda: Mock,
    mock_extract_test_command_params: Mock,
    mock_boto_client: Mock,
    mock_logger,
):
    """Test redirect to PR lambda"""
    with patch("app.core.config.get_logger", return_value=mock_logger):
        # setup mock
        mock_client = Mock()

        pr_number = "123"
        user_id = "U456"
        slack_command_data = {
            "text": f"pr: {pr_number}",
            "user_id": user_id,
            "channel_id": "C789",
            "ts": "1234567890.123",
            "command": "/test",
        }

        # perform operation
        # delete and import module to test
        if "app.slack.slack_handlers" in sys.modules:
            del sys.modules["app.slack.slack_handlers"]
        from app.slack.slack_handlers import command_handler

        mock_extract_test_command_params.return_value = {"pr": pr_number}

        command_handler(slack_command_data, slack_command_data, mock_client)

        # assertions
        mock_forward_to_pull_request_lambda.assert_called_once()
        mock_extract_test_command_params.assert_called_once()
        mock_logger.info.assert_called_with(f"Command in pull request session {pr_number} from user {user_id}")


@patch("app.slack.slack_events.process_async_slack_command")
@patch("app.utils.handler_utils.forward_to_pull_request_lambda")
def test_process_slack_command_handler_no_command(
    mock_forward_to_pull_request_lambda: Mock, mock_process_async_slack_command: Mock, mock_logger
):
    """Test redirect to PR lambda"""
    with patch("app.core.config.get_logger", return_value=mock_logger):
        # setup mock
        mock_client = Mock()

        slack_command_data = None

        # perform operation
        # delete and import module to test
        if "app.slack.slack_handlers" in sys.modules:
            del sys.modules["app.slack.slack_handlers"]
        from app.slack.slack_handlers import command_handler

        command_handler(slack_command_data, slack_command_data, mock_client)

        # assertions
        mock_forward_to_pull_request_lambda.assert_not_called()
        mock_process_async_slack_command.assert_not_called()
        mock_logger.error.assert_called_once()


@pytest.fixture(scope="module")
@patch("app.services.bedrock.query_bedrock")
def test_process_slack_command_test_questions_ai_request_to_file(
    mock_query_bedrock: Mock,
):
    """Test successful command processing"""
    # set up mocks
    mock_client = Mock()

    # import module to test
    from app.slack.slack_events import process_async_slack_command

    # perform operation
    slack_command_data = {
        "text": "",
        "user_id": "U456",
        "channel_id": "C789",
        "ts": "1234567890.123",
        "command": "/test",
    }

    mock_response = MagicMock()
    mock_response.data = {}
    mock_response.get.side_effect = lambda k: {"thread_ts": "1234567890.123456", "channel": "C12345678"}.get(k)
    mock_client.chat_postMessage.return_value = mock_response

    # perform operation
    process_async_slack_command(command=slack_command_data, client=mock_client)

    # assertions
    assert mock_query_bedrock.call_count == 21


@patch("app.services.ai_processor.process_ai_query")
@patch("app.slack.slack_events.process_command_test_ai_request")
def test_process_slack_command_test_questions_default_to_file(
    mock_process_command_test_ai_request: Mock,
    mock_process_ai_query: Mock,
):
    """Test successful command processing"""
    # set up mocks
    mock_client = Mock()

    # import module to test
    from app.slack.slack_events import process_async_slack_command

    # perform operation
    slack_command_data = {
        "text": "",
        "user_id": "U456",
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
    mock_client.chat_postMessage.assert_not_called()
    mock_client.files_upload_v2.assert_called_once()
    assert mock_process_command_test_ai_request.call_count == 21


@patch("app.services.ai_processor.process_ai_query")
@patch("app.slack.slack_events.process_command_test_ai_request")
def test_process_slack_command_test_questions_single_question_to_file(
    mock_process_command_test_ai_request: Mock,
    mock_process_ai_query: Mock,
):
    """Test successful command processing"""
    # set up mocks
    mock_client = Mock()

    mock_client.retrieve_and_generate.return_value = {"output": {"text": "bedrock response"}}
    # delete and import module to test
    from app.slack.slack_events import process_async_slack_command

    # perform operation
    slack_command_data = {
        "text": "q2",
        "user_id": "U456",
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
    mock_client.chat_postMessage.assert_not_called()
    mock_client.files_upload_v2.assert_called_once()
    assert mock_process_command_test_ai_request.call_count == 1


@patch("app.services.ai_processor.process_ai_query")
@patch("app.slack.slack_events.process_command_test_ai_request")
def test_process_slack_command_test_questions_two_questions_to_file(
    mock_process_command_test_ai_request: Mock,
    mock_process_ai_query: Mock,
):
    """Test successful command processing"""
    # set up mocks
    mock_client = Mock()

    from app.slack.slack_events import process_async_slack_command

    # perform operation
    slack_command_data = {
        "text": "q2-3",
        "user_id": "U456",
        "channel_id": "C789",
        "ts": "1234567890.123",
        "command": "/test",
    }

    mock_client.chat_postMessage.return_value = {}
    mock_process_command_test_ai_request.return_value = "test"

    mock_process_ai_query.return_value = {"text": "ai response", "session_id": None, "citations": [], "kb_response": {}}

    # perform operation
    process_async_slack_command(command=slack_command_data, client=mock_client)

    # assertions
    mock_client.chat_postMessage.assert_not_called()
    mock_client.files_upload_v2.assert_called_once()
    assert mock_process_command_test_ai_request.call_count == 2


@pytest.fixture(scope="module")
@patch("app.services.bedrock.query_bedrock")
def test_process_slack_command_test_questions_ai_request_to_slack(
    mock_query_bedrock: Mock,
):
    """Test successful command processing"""
    # set up mocks
    mock_client = Mock()

    # import module to test
    from app.slack.slack_events import process_async_slack_command

    # perform operation
    slack_command_data = {
        "text": "output",
        "user_id": "U456",
        "channel_id": "C789",
        "ts": "1234567890.123",
        "command": "/test",
    }

    mock_response = MagicMock()
    mock_response.data = {}
    mock_response.get.side_effect = lambda k: {"thread_ts": "1234567890.123456", "channel": "C12345678"}.get(k)
    mock_client.chat_postMessage.return_value = mock_response

    # perform operation
    process_async_slack_command(command=slack_command_data, client=mock_client)

    # assertions
    assert mock_query_bedrock.call_count == 21


@patch("app.services.ai_processor.process_ai_query")
def test_process_slack_command_test_questions_default_to_slack(
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
        "text": "output",
        "user_id": "U456",
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
    assert (
        mock_client.chat_postMessage.call_count == 42
    )  # 21 Tests - Posts once with question information, then replies with answer


@patch("app.services.ai_processor.process_ai_query")
def test_process_slack_command_test_questions_single_question_to_slack(
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
        "text": "q2 output",
        "user_id": "U456",
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
    assert mock_client.chat_postMessage.call_count == 2  # 1 questions + 1 answers


@patch("app.services.ai_processor.process_ai_query")
def test_process_slack_command_test_questions_two_questions_to_slack(
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
        "text": "q2-3 output",
        "user_id": "U456",
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
    assert mock_client.chat_postMessage.call_count == 4  # 2 questions + 2 answers


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
            "user_id": "U456",
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
        "user_id": "U456",
        "channel_id": "C789",
        "ts": "1234567890.123",
        "command": "/test",
    }

    mock_response = MagicMock()
    mock_response.data = {}
    mock_client.chat_postEphemeral.return_value = mock_response

    mock_process_ai_query.return_value = {"text": "ai response", "session_id": None, "citations": [], "kb_response": {}}

    # perform operation
    process_async_slack_command(command=slack_command_data, client=mock_client)

    # assertions
    mock_client.chat_postMessage.assert_not_called()
    mock_client.chat_postEphemeral.assert_called()
