import pytest
from unittest.mock import patch
import os


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    env_vars = {
        "SLACK_BOT_TOKEN_PARAMETER": "/test/bot-token",
        "SLACK_SIGNING_SECRET_PARAMETER": "/test/signing-secret",
        "SLACK_BOT_STATE_TABLE": "test-bot-state-table",
        "KNOWLEDGEBASE_ID": "test-kb-id",
        "RAG_MODEL_ID": "test-model-id",
        "AWS_REGION": "eu-west-2",
        "GUARD_RAIL_ID": "test-guard-id",
        "GUARD_RAIL_VERSION": "1",
        "AWS_LAMBDA_FUNCTION_NAME": "test-function",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@patch("app.slack.slack_events.table")
@patch("time.time")
def test_store_feedback(mock_time, mock_table, mock_env):
    """Test feedback storage functionality"""
    mock_time.return_value = 1000

    from app.slack.slack_events import store_feedback

    store_feedback("test-conversation", "test query", "positive", "U123", "C123")

    mock_table.put_item.assert_called_once()
    call_args = mock_table.put_item.call_args[1]["Item"]
    assert call_args["feedback_type"] == "positive"
    assert call_args["user_query"] == "test query"
    assert call_args["user_id"] == "U123"


@patch("app.slack.slack_events.store_feedback")
def test_feedback_storage_with_additional_text(mock_store_feedback, mock_env):
    """Test feedback storage with additional feedback text"""
    from app.slack.slack_events import store_feedback

    store_feedback("test-conversation", "test query", "additional", "U123", "This is additional feedback")

    mock_store_feedback.assert_called_once_with(
        "test-conversation", "test query", "additional", "U123", "This is additional feedback"
    )


def test_feedback_message_empty_text(mock_env):
    """Test that empty feedback doesn't crash"""
    from app.slack.slack_handlers import _gate_common, _strip_mentions, _conversation_key_and_root
    from app.slack.slack_events import get_conversation_session

    # Test _gate_common helper functions
    result = _gate_common({}, {})
    assert result is None

    result = _gate_common({"bot_id": "B123"}, {"event_id": "evt123"})
    assert result is None

    # Test strip mentions
    result = _strip_mentions("<@U123> hello world")
    assert result == "hello world"

    # Test conversation key for DM
    event = {"channel": "D123", "ts": "456", "channel_type": "im"}
    key, root = _conversation_key_and_root(event)
    assert key == "dm#D123"
    assert root == "456"

    # Test error handling
    with patch("app.core.config.table") as mock_table:
        mock_table.get_item.side_effect = Exception("DB error")
        result = get_conversation_session("test-conv")
        assert result is None


@patch("app.slack.slack_events.table")
def test_store_qa_pair_error_handling(mock_table, mock_env):
    """Test store_qa_pair error handling"""
    mock_table.put_item.side_effect = Exception("DB error")
    from app.slack.slack_events import store_qa_pair

    # Should not raise exception
    store_qa_pair("conv-key", "query", "response", "123", "session-id", "user-id")


@patch("app.slack.slack_events.table")
def test_store_conversation_session_error_handling(mock_table, mock_env):
    """Test store_conversation_session error handling"""
    mock_table.put_item.side_effect = Exception("DB error")
    from app.slack.slack_events import store_conversation_session

    # Should not raise exception
    store_conversation_session("conv-key", "session-id", "user-id", "channel-id")


@patch("app.slack.slack_events.table")
def test_update_session_latest_message_error_handling(mock_table, mock_env):
    """Test update_session_latest_message error handling"""
    mock_table.update_item.side_effect = Exception("DB error")
    from app.slack.slack_events import update_session_latest_message

    # Should not raise exception
    update_session_latest_message("conv-key", "123")


@patch("app.slack.slack_events.table")
@patch("time.time")
def test_store_feedback_with_qa_fallback_paths(mock_time, mock_table, mock_env):
    """Test store_feedback_with_qa fallback paths"""
    mock_time.return_value = 1000
    from app.slack.slack_events import store_feedback_with_qa

    with patch("app.slack.slack_events.get_latest_message_ts", return_value=None):
        store_feedback_with_qa("conv-key", "query", "response", "positive", "user-id", "channel-id")
        mock_table.put_item.assert_called()


@patch("app.slack.slack_events.table")
def test_cleanup_previous_unfeedback_qa(mock_table, mock_env):
    """Test cleanup_previous_unfeedback_qa function"""
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    # Test with no previous message
    session_data = {}
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)
    mock_table.delete_item.assert_not_called()

    # Test with same message timestamp
    session_data = {"latest_message_ts": "123"}
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)
    mock_table.delete_item.assert_not_called()

    # Test with different message timestamp and no feedback
    mock_table.reset_mock()
    session_data = {"latest_message_ts": "456"}
    with patch("app.slack.slack_events.check_feedback_exists", return_value=False):
        cleanup_previous_unfeedback_qa("conv-key", "123", session_data)
        mock_table.delete_item.assert_called_once_with(Key={"pk": "qa#conv-key#456", "sk": "turn"})

    # Test with different message timestamp and existing feedback
    mock_table.reset_mock()
    with patch("app.slack.slack_events.check_feedback_exists", return_value=True):
        cleanup_previous_unfeedback_qa("conv-key", "123", session_data)
        mock_table.delete_item.assert_not_called()


@patch("app.slack.slack_events.table")
def test_check_feedback_exists(mock_table, mock_env):
    """Test check_feedback_exists function"""
    from app.slack.slack_events import check_feedback_exists

    # Test with existing feedback
    mock_table.query.return_value = {"Items": [{"feedback_type": "positive"}]}
    result = check_feedback_exists("conv-key", "123")
    assert result is True

    # Test with no feedback
    mock_table.query.return_value = {"Items": []}
    result = check_feedback_exists("conv-key", "123")
    assert result is False

    # Test with exception
    mock_table.query.side_effect = Exception("DB error")
    result = check_feedback_exists("conv-key", "123")
    assert result is False


@patch("app.slack.slack_events.table")
def test_cleanup_previous_unfeedback_qa_error_handling(mock_table, mock_env):
    """Test cleanup_previous_unfeedback_qa error handling"""
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    session_data = {"latest_message_ts": "456"}
    with patch("app.slack.slack_events.check_feedback_exists", side_effect=Exception("Error")):
        # Should not raise exception
        cleanup_previous_unfeedback_qa("conv-key", "123", session_data)


@patch("app.slack.slack_events.table")
def test_get_conversation_session_data_no_item(mock_table, mock_env):
    """Test get_conversation_session_data when no item exists"""
    mock_table.get_item.return_value = {}  # No Item key
    from app.slack.slack_events import get_conversation_session_data

    result = get_conversation_session_data("test-key")
    assert result is None


@patch("app.slack.slack_events.table")
def test_get_latest_message_ts_no_item(mock_table, mock_env):
    """Test get_latest_message_ts when no item exists"""
    mock_table.get_item.return_value = {}  # No Item key
    from app.slack.slack_events import get_latest_message_ts

    result = get_latest_message_ts("test-key")
    assert result is None


@patch("app.slack.slack_events.table")
def test_store_feedback_client_error_reraise(mock_table, mock_env):
    """Test store_feedback re-raises ClientError"""
    from botocore.exceptions import ClientError

    error = ClientError({"Error": {"Code": "ValidationException"}}, "PutItem")
    mock_table.put_item.side_effect = error

    from app.slack.slack_events import store_feedback

    with patch("app.slack.slack_events.get_latest_message_ts", return_value="123"):
        with pytest.raises(ClientError):
            store_feedback("conv-key", "query", "positive", "user-id", "channel-id")
