import sys
import pytest
from unittest.mock import patch
from botocore.exceptions import ClientError


@patch("app.services.dynamo.store_state_information")
@patch("app.services.dynamo.get_state_information")
def test_store_feedback(mock_get_state_information, mock_store_state_information, mock_env):
    """Test feedback storage functionality"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    from app.slack.slack_events import store_feedback

    store_feedback("test-conversation", "positive", "U123", "C123")

    mock_store_state_information.assert_called_once()
    call_args = mock_store_state_information.call_args.kwargs["item"]
    assert call_args["feedback_type"] == "positive"
    assert call_args["user_id"] == "U123"


@patch("app.services.dynamo.store_state_information")
@patch("app.services.dynamo.get_state_information")
def test_feedback_storage_with_additional_text(mock_get_state_information, mock_store_state_information, mock_env):
    """Test feedback storage with additional feedback text"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_feedback

    store_feedback("test-conversation", "additional", "U123", "C123", feedback_text="This is additional feedback")

    mock_store_state_information.assert_called_once()
    call_args = mock_store_state_information.call_args.kwargs["item"]
    assert call_args["feedback_type"] == "additional"
    assert call_args["user_id"] == "U123"
    assert call_args["feedback_text"] == "This is additional feedback"


def test_feedback_message_empty_text(mock_env):
    """Test that empty feedback doesn't crash"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _gate_common, _strip_mentions, _conversation_key_and_root

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


@patch("app.services.dynamo.store_state_information")
def test_store_qa_pair_error_handling(mock_store_state_information, mock_env):
    """Test store_qa_pair error handling"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_qa_pair

    # Should not raise exception
    store_qa_pair("conv-key", "query", "response", "123", "session-id", "user-id")
    mock_store_state_information.assert_called_once()


@patch("app.services.dynamo.store_state_information")
def test_store_conversation_session_error_handling(mock_store_state_information, mock_env):
    """Test store_conversation_session error handling"""
    mock_store_state_information.side_effect = Exception("DB error")
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_conversation_session

    # Should not raise exception
    store_conversation_session("conv-key", "session-id", "user-id", "channel-id")


@patch("app.services.dynamo.store_state_information")
def test_update_session_latest_message_error_handling(mock_store_state_information, mock_env):
    """Test update_session_latest_message error handling"""
    mock_store_state_information.side_effect = Exception("DB error")
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import update_session_latest_message

    # Should not raise exception
    update_session_latest_message("conv-key", "123")


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_no_previous_message(delete_state_information, mock_env):
    """Test cleanup_previous_unfeedback_qa function"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    # Test with no previous message
    session_data = {}
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)
    delete_state_information.assert_not_called()


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_same_timestamp(delete_state_information, mock_env):
    # Test with same message timestamp
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    session_data = {"latest_message_ts": "123"}
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)
    delete_state_information.assert_not_called()


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_newer_timestamp(delete_state_information, mock_env):
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    session_data = {"latest_message_ts": "456"}
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)
    delete_state_information.assert_called()


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_does_not_throw_error(delete_state_information, mock_env):
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    session_data = {}
    error = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "DeleteItem")
    delete_state_information.side_effect = error
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)


@patch("app.services.dynamo.store_state_information")
def test_store_feedback_no_message_ts_fallback(mock_store_state_information, mock_env):
    """Test store_feedback fallback path when no message_ts"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_feedback

    with patch("app.slack.slack_events.get_latest_message_ts", return_value=None):
        store_feedback("conv-key", "positive", "user-id", "channel-id")
        mock_store_state_information.assert_called_once()
        # Should use fallback pk/sk format without condition
        call_args = mock_store_state_information.call_args.kwargs
        assert "ConditionExpression" not in call_args
        item = call_args["item"]
        assert item["pk"] == "feedback#conv-key"
        assert "#note#" in item["sk"]


@patch("app.services.dynamo.store_state_information")
@patch("app.services.dynamo.get_state_information")
def test_store_conversation_session_with_thread(mock_get_state_information, mock_store_state_information, mock_env):
    """Test store_conversation_session with thread_ts"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_conversation_session

    store_conversation_session("conv-key", "session-id", "user-id", "channel-id", "thread-123", "msg-456")
    mock_store_state_information.assert_called_once()
    item = mock_store_state_information.call_args.kwargs["item"]
    assert item["thread_ts"] == "thread-123"
    assert item["latest_message_ts"] == "msg-456"


@patch("app.services.dynamo.store_state_information")
@patch("app.services.dynamo.get_state_information")
def test_store_conversation_session_without_thread(mock_get_state_information, mock_store_state_information, mock_env):
    """Test store_conversation_session without thread_ts"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_conversation_session

    store_conversation_session("conv-key", "session-id", "user-id", "channel-id")
    mock_store_state_information.assert_called_once()
    item = mock_store_state_information.call_args.kwargs["item"]
    assert "thread_ts" not in item
    assert "latest_message_ts" not in item


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_error_handling(mock_delete_state_information, mock_env):
    """Test cleanup_previous_unfeedback_qa error handling"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    session_data = {"latest_message_ts": "456"}
    mock_delete_state_information.side_effect = Exception("DB error")
    # Should not raise exception
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)


@patch("app.services.dynamo.get_state_information")
def test_get_conversation_session_data_no_item(mock_get_state_information, mock_env):
    """Test get_conversation_session_data when no item exists"""
    mock_get_state_information.return_value = {}  # No Item key
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import get_conversation_session_data

    result = get_conversation_session_data("test-key")
    assert result is None


@patch("app.services.dynamo.get_state_information")
def test_get_latest_message_ts_no_item(mock_get_state_information, mock_env):
    """Test get_latest_message_ts when no item exists"""
    mock_get_state_information.return_value = {}  # No Item key
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import get_latest_message_ts

    result = get_latest_message_ts("test-key")
    assert result is None


@patch("app.services.dynamo.store_state_information")
def test_store_feedback_client_error_reraise(mock_store_state_information, mock_env):
    """Test store_feedback re-raises ClientError"""

    error = ClientError({"Error": {"Code": "ValidationException"}}, "PutItem")
    mock_store_state_information.side_effect = error

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_feedback

    with patch("app.slack.slack_events.get_latest_message_ts", return_value="123"):
        with pytest.raises(ClientError):
            store_feedback("conv-key", "positive", "user-id", "channel-id")


@patch("app.services.dynamo.store_state_information")
def test_mark_qa_feedback_received_error(mock_store_state_information, mock_env):
    """Test _mark_qa_feedback_received error handling"""
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _mark_qa_feedback_received

    mock_store_state_information.side_effect = Exception("DB error")

    # Should not raise exception
    _mark_qa_feedback_received("conv-key", "123")
