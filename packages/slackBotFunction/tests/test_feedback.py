import sys
import pytest
from unittest.mock import patch
from botocore.exceptions import ClientError


@patch("app.services.dynamo.store_state_information")
@patch("app.services.dynamo.get_state_information")
def test_store_feedback(mock_get_state_information, mock_store_state_information, mock_env):
    """Test feedback storage functionality"""
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_feedback

    # perform operation
    store_feedback("test-conversation", "positive", "U123", "C123")

    # assertions
    mock_store_state_information.assert_called_once()
    call_args = mock_store_state_information.call_args.kwargs["item"]
    assert call_args["feedback_type"] == "positive"
    assert call_args["user_id"] == "U123"


@patch("app.services.dynamo.store_state_information")
@patch("app.services.dynamo.get_state_information")
def test_feedback_storage_with_additional_text(mock_get_state_information, mock_store_state_information, mock_env):
    """Test feedback storage with additional feedback text"""
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_feedback

    # perform operation
    store_feedback("test-conversation", "additional", "U123", "C123", feedback_text="This is additional feedback")

    # assertions
    mock_store_state_information.assert_called_once()
    call_args = mock_store_state_information.call_args.kwargs["item"]
    assert call_args["feedback_type"] == "additional"
    assert call_args["user_id"] == "U123"
    assert call_args["feedback_text"] == "This is additional feedback"


def test_gate_common_empty_vars(mock_env):
    """Test that empty feedback doesn't crash"""
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _gate_common

    # perform operation
    result = _gate_common({}, {})

    # assertions
    assert result is None


def test_gate_common_populated_vars(mock_env):
    """Test that empty feedback doesn't crash"""
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _gate_common

    # perform operation
    result = _gate_common({"bot_id": "B123"}, {"event_id": "evt123"})

    # assertions
    assert result is None


def test_strip_mentions(mock_env):
    """Test that empty feedback doesn't crash"""
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _strip_mentions

    # perform operation
    result = _strip_mentions("<@U123> hello world")

    # assertions
    assert result == "hello world"


def test_extract_key_and_root(mock_env):
    """Test that empty feedback doesn't crash"""
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _conversation_key_and_root

    # perform operation
    event = {"channel": "D123", "ts": "456", "channel_type": "im"}
    key, root = _conversation_key_and_root(event)

    # assertions
    assert key == "dm#D123"
    assert root == "456"


@patch("app.services.dynamo.store_state_information")
def test_store_qa_pair_error_handling(mock_store_state_information, mock_env):
    """Test store_qa_pair error handling"""
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_qa_pair

    # perform operation
    store_qa_pair("conv-key", "query", "response", "123", "session-id", "user-id")

    # assertions
    mock_store_state_information.assert_called_once()


@patch("app.services.dynamo.store_state_information")
def test_store_conversation_session_error_handling(mock_store_state_information, mock_env):
    """Test store_conversation_session error handling"""
    # set up mocks
    mock_store_state_information.side_effect = Exception("DB error")

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_conversation_session

    # perform operation
    store_conversation_session("conv-key", "session-id", "user-id", "channel-id")

    # assertions
    # we are just checking it does not throw an error


@patch("app.services.dynamo.store_state_information")
def test_update_session_latest_message_error_handling(mock_store_state_information, mock_env):
    """Test update_session_latest_message error handling"""
    # set up mocks
    mock_store_state_information.side_effect = Exception("DB error")

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import update_session_latest_message

    # perform operation
    update_session_latest_message("conv-key", "123")

    # assertions
    # we are just checking it does not throw an error


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_no_previous_message(delete_state_information, mock_env):
    """Test cleanup_previous_unfeedback_qa function"""
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    # perform operation
    session_data = {}
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)

    # assertions
    delete_state_information.assert_not_called()


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_same_timestamp(delete_state_information, mock_env):
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    # perform operation
    session_data = {"latest_message_ts": "123"}
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)

    # assertions
    delete_state_information.assert_not_called()


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_newer_timestamp(delete_state_information, mock_env):
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    # perform operation
    session_data = {"latest_message_ts": "456"}
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)

    # assertions
    delete_state_information.assert_called()


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_does_not_throw_error(delete_state_information, mock_env):
    # set up mocks
    error = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "DeleteItem")
    delete_state_information.side_effect = error

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    # perform operation
    session_data = {}
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)

    # assertions
    # we are just checking that no error is thrown


@patch("app.services.dynamo.store_state_information")
@patch("app.slack.slack_events.get_latest_message_ts")
def test_store_feedback_no_message_ts_fallback(mock_get_latest_message_ts, mock_store_state_information, mock_env):
    """Test store_feedback fallback path when no message_ts"""
    # set up mocks
    mock_get_latest_message_ts.return_value = None

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_feedback

    # perform operation
    store_feedback("conv-key", "positive", "user-id", "channel-id")

    # assertions
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
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_conversation_session

    # perform operation
    store_conversation_session("conv-key", "session-id", "user-id", "channel-id", "thread-123", "msg-456")

    # assertions
    mock_store_state_information.assert_called_once()
    item = mock_store_state_information.call_args.kwargs["item"]
    assert item["thread_ts"] == "thread-123"
    assert item["latest_message_ts"] == "msg-456"


@patch("app.services.dynamo.store_state_information")
@patch("app.services.dynamo.get_state_information")
def test_store_conversation_session_without_thread(mock_get_state_information, mock_store_state_information, mock_env):
    """Test store_conversation_session without thread_ts"""
    # set up mocks

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_conversation_session

    # perform operation
    store_conversation_session("conv-key", "session-id", "user-id", "channel-id")

    # assertions
    mock_store_state_information.assert_called_once()
    item = mock_store_state_information.call_args.kwargs["item"]
    assert "thread_ts" not in item
    assert "latest_message_ts" not in item


@patch("app.services.dynamo.delete_state_information")
def test_cleanup_previous_unfeedback_qa_error_handling(mock_delete_state_information, mock_env):
    """Test cleanup_previous_unfeedback_qa error handling"""
    # set up mocks
    mock_delete_state_information.side_effect = Exception("DB error")

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import cleanup_previous_unfeedback_qa

    # perform operation
    session_data = {"latest_message_ts": "456"}
    cleanup_previous_unfeedback_qa("conv-key", "123", session_data)

    # assertions
    # we are just testing it does not throw an error


@patch("app.services.dynamo.get_state_information")
def test_get_conversation_session_data_no_item(mock_get_state_information, mock_env):
    """Test get_conversation_session_data when no item exists"""
    # set up mocks
    mock_get_state_information.return_value = {}  # No Item key

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import get_conversation_session_data

    # perform operation
    result = get_conversation_session_data("test-key")

    # assertions
    assert result is None


@patch("app.services.dynamo.get_state_information")
def test_get_latest_message_ts_no_item(mock_get_state_information, mock_env):
    """Test get_latest_message_ts when no item exists"""
    # set up mocks
    mock_get_state_information.return_value = {}  # No Item key

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import get_latest_message_ts

    # perform operation
    result = get_latest_message_ts("test-key")

    # assertions
    assert result is None


@patch("app.services.dynamo.store_state_information")
@patch("app.slack.slack_events.get_latest_message_ts")
def test_store_feedback_client_error_reraise(mock_get_latest_message_ts, mock_store_state_information, mock_env):
    """Test store_feedback re-raises ClientError"""
    # set up mocks
    error = ClientError({"Error": {"Code": "ValidationException"}}, "PutItem")
    mock_store_state_information.side_effect = error
    mock_get_latest_message_ts.return_value = "123"

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import store_feedback

    # perform operation
    with pytest.raises(ClientError):
        store_feedback("conv-key", "positive", "user-id", "channel-id")


@patch("app.services.dynamo.store_state_information")
def test_mark_qa_feedback_received_error(mock_store_state_information, mock_env):
    """Test _mark_qa_feedback_received error handling"""
    # set up mocks
    mock_store_state_information.side_effect = Exception("DB error")

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _mark_qa_feedback_received

    # perform operation
    _mark_qa_feedback_received("conv-key", "123")

    # assertions
    # we are just checking no exception is thrown
