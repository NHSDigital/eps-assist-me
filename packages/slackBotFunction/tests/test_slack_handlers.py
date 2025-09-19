import sys
from unittest.mock import ANY, Mock, patch
from botocore.exceptions import ClientError


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_app_mention_handler(
    mock_respond_with_eyes: Mock,
    mock_trigger_async_processing: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test app mention handler execution"""
    # set up mocks
    mock_ack = Mock()
    mock_event = {
        "user": "U123",
        "text": "<@U456> test",
        "channel": "C123",
        "thread_ts": "123",
        "channel_type": "channel",
    }
    mock_body = {"event_id": "evt123"}
    mock_client = Mock()
    mock_is_duplicate_event.return_value = False

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    # perform operation
    mention_handler(mock_event, mock_ack, mock_body, mock_client)

    # assertions
    mock_ack.assert_called_once()
    mock_trigger_async_processing.assert_called_once_with(event=mock_event, event_id="evt123")
    mock_respond_with_eyes.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_message_handler_non_dm_skip(
    mock_respond_with_eyes: Mock,
    mock_trigger_async_processing: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test message handler skips non-DM messages"""
    # set up mocks
    mock_is_duplicate_event.return_value = False
    mock_ack = Mock()
    mock_event = {"text": "regular message", "channel_type": "channel", "channel": "C123"}  # Not "im"
    mock_body = {"event_id": "evt123"}
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import unified_message_handler

    # Test non-DM skip
    unified_message_handler(mock_event, mock_ack, mock_body, mock_client)

    # assertions
    mock_ack.assert_called_once()
    mock_trigger_async_processing.assert_not_called()  # Should not trigger for non-DM
    mock_respond_with_eyes.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.utils.handler_utils.is_latest_message")
@patch("app.slack.slack_events.store_feedback")
def test_feedback_action_handler(
    mock_store_feedback: Mock,
    mock_is_latest_message: Mock,
    mock_respond_with_eyes: Mock,
    mock_trigger_async_processing: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback_yes action handler"""
    # setup mocks
    mock_is_latest_message.return_value = True

    mock_ack = Mock()
    mock_body = {
        "user": {"id": "U123"},
        "actions": [
            {"action_id": "feedback_yes", "value": '{"ck": "conv-key", "ch": "C123", "tt": "123", "mt": "456"}'}
        ],
        "channel": {"id": "C123"},
        "message": {"ts": "123"},
    }
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    # perform operation
    feedback_handler(mock_ack, mock_body, mock_client)

    # assertions
    mock_ack.assert_called_once()
    mock_store_feedback.assert_called_once_with(
        conversation_key="conv-key",
        feedback_type="positive",
        user_id="U123",
        channel_id="C123",
        thread_ts="123",
        message_ts="456",
        client=ANY,
    )
    mock_client.chat_postMessage.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_duplicate_event_skip_processing(
    mock_respond_with_eyes: Mock,
    mock_trigger_async_processing: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test that duplicate events skip processing"""
    # setup mocks
    mock_ack = Mock()
    mock_event = {"user": "U123", "text": "test", "channel": "C123"}
    mock_body = {"event_id": "evt123"}
    mock_client = Mock()
    mock_is_duplicate_event.return_value = True

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    # perform operation
    mention_handler(mock_event, mock_ack, mock_body, mock_client)

    # assertions
    mock_ack.assert_called_once()
    mock_trigger_async_processing.assert_not_called()  # Should not trigger for duplicate


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
def test_app_mention_feedback_store_feedback_error_handling(
    mock_store_feedback: Mock,
    mock_respond_with_eyes: Mock,
    mock_trigger_async_processing: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test app mention feedback error handling"""
    # setup mocks
    mock_ack = Mock()
    mock_client = Mock()
    mock_event = {"text": "<@U123> feedback: this is feedback", "user": "U456", "channel": "C789", "ts": "123"}
    mock_body = {"event_id": "evt123"}
    mock_is_duplicate_event.return_value = False

    mock_store_feedback.side_effect = Exception("Storage failed")

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    # perform operation
    mention_handler(mock_event, mock_ack, mock_body, mock_client)

    # assertions
    # Should still try to post message
    mock_client.chat_postMessage.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
def test_app_mention_feedback_post_error_handling(
    mock_store_feedback: Mock,
    mock_respond_with_eyes: Mock,
    mock_trigger_async_processing: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test app mention feedback error handling"""
    # setup mocks
    mock_ack = Mock()
    mock_client = Mock()
    mock_event = {"text": "<@U123> feedback: this is feedback", "user": "U456", "channel": "C789", "ts": "123"}
    mock_body = {"event_id": "evt123"}
    mock_client.chat_postMessage.side_effect = Exception("Post failed")

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    # perform operation
    mention_handler(mock_event, mock_ack, mock_body, mock_client)

    # assertions
    # Should not raise exception


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
def test_dm_message_handler_feedback_error_handling(
    mock_store_feedback: Mock,
    mock_respond_with_eyes: Mock,
    mock_trigger_async_processing: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test DM message handler feedback error handling"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "feedback: DM feedback", "user": "U456", "channel": "D789", "ts": "123", "channel_type": "im"}
    mock_body = {}
    mock_store_feedback.side_effect = Exception("Storage failed")

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import dm_message_handler

    # perform operation
    dm_message_handler(mock_event, "evt123", mock_client, mock_body)

    # assertions
    mock_client.chat_postMessage.assert_called_once()


@patch("app.services.dynamo.get_state_information")
def test_thread_message_handler_session_check_error(
    mock_get_state_information: Mock, mock_get_parameter: Mock, mock_env: Mock
):
    """Test thread_message_handler session check error"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "follow up", "channel": "C789", "thread_ts": "123", "user": "U456"}
    mock_body = {}

    mock_get_state_information.side_effect = Exception("DB error")

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import thread_message_handler

    # perform operation
    # Should return early due to error
    thread_message_handler(mock_event, "evt123", mock_client, mock_body)

    # assertions


def test_feedback_handler_unknown_action(mock_env: Mock):
    """Test feedback_handler with unknown action"""
    # setup mocks
    mock_ack = Mock()
    mock_body = {"actions": [{"action_id": "unknown_action", "value": "{}"}]}
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    # perform operation
    feedback_handler(mock_ack, mock_body, mock_client)

    # assertions
    mock_ack.assert_called_once()


@patch("app.utils.handler_utils.is_latest_message")
def test_feedback_handler_not_latest_message(mock_is_latest_message: Mock, mock_env: Mock):
    """Test feedback_handler when not latest message"""
    # setup mocks
    mock_ack = Mock()
    mock_body = {"actions": [{"action_id": "feedback_yes", "value": '{"ck": "conv-key", "mt": "123"}'}]}
    mock_client = Mock()
    mock_is_latest_message.return_value = True

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    # perform operation
    feedback_handler(mock_ack, mock_body, mock_client)

    # assertions
    mock_ack.assert_called_once()


@patch("app.services.dynamo.get_state_information")
def test_thread_message_handler_no_session(mock_get_state_information: Mock, mock_env: Mock):
    """Test thread_message_handler when no session found"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "follow up", "channel": "C789", "thread_ts": "123", "user": "U456"}
    mock_body = {}

    mock_get_state_information.return_value = {}  # No session

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import thread_message_handler

    # perform operation
    thread_message_handler(mock_event, "evt123", mock_client, mock_body)

    # assertions
    # we just want to test it does not throw error


@patch("app.services.dynamo.get_state_information")
def test_thread_message_handler_feedback_path(mock_get_state_information: Mock, mock_env: Mock):
    """Test thread_message_handler feedback path"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "feedback: channel feedback", "channel": "C789", "thread_ts": "123", "user": "U456"}
    mock_body = {}

    mock_get_state_information.return_value = {"Item": {"session_id": "session123"}}

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import thread_message_handler

    # perform operation
    thread_message_handler(mock_event, "evt123", mock_client, mock_body)

    # assertions
    # we just want to test it does not throw error


@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_dm_message_handler_normal_message(
    mock_respond_with_eyes: Mock, mock_trigger_async_processing: Mock, mock_get_parameter: Mock, mock_env: Mock
):
    """Test dm_message_handler with normal message"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "normal message", "user": "U456", "channel": "D789", "ts": "123", "channel_type": "im"}
    mock_body = {}

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import dm_message_handler

    # perform operation
    dm_message_handler(mock_event, "evt123", mock_client, mock_body)

    # assertions
    mock_trigger_async_processing.assert_called_once()


@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.utils.handler_utils.is_duplicate_event")
def test_mention_handler_normal_mention(
    mock_is_duplicate_event: Mock,
    mock_respond_with_eyes: Mock,
    mock_trigger_async_processing: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test mention_handler with normal mention"""
    # setup mocks
    mock_ack = Mock()
    mock_client = Mock()
    mock_event = {"text": "<@U123> normal question", "user": "U456", "channel": "C789", "ts": "123"}
    mock_body = {"event_id": "evt123"}
    mock_is_duplicate_event.return_value = False

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    # perform operation
    mention_handler(mock_event, mock_ack, mock_body, mock_client)

    # assertions
    mock_trigger_async_processing.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
@patch("app.utils.handler_utils.is_latest_message")
def test_feedback_handler_conditional_check_failed(
    mock_is_latest_message: Mock,
    mock_store_feedback: Mock,
    mock_respond_with_eyes: Mock,
    mock_trigger_async_processing: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback_handler with ConditionalCheckFailedException"""
    # setup mocks
    mock_is_latest_message.return_value = True
    mock_ack = Mock()
    mock_body = {
        "user": {"id": "U123"},
        "actions": [{"action_id": "feedback_yes", "value": '{"ck": "conv-key", "mt": "123"}'}],
    }
    mock_client = Mock()

    error = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
    mock_store_feedback.side_effect = error

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    # perform operation
    feedback_handler(mock_ack, mock_body, mock_client)

    # assertions
    mock_ack.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
@patch("app.utils.handler_utils.is_latest_message")
def test_feedback_handler_storage_error(
    mock_is_latest_message: Mock,
    mock_store_feedback: Mock,
    mock_respond_with_eyes: Mock,
    mock_trigger_async_processing: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback_handler with storage error"""
    # setup mocks
    mock_is_latest_message.return_value = True
    mock_ack = Mock()
    mock_body = {
        "user": {"id": "U123"},
        "actions": [{"action_id": "feedback_yes", "value": '{"ck": "conv-key", "mt": "123"}'}],
    }
    mock_client = Mock()
    mock_store_feedback.side_effect = Exception("Storage error")

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    # perform operation
    feedback_handler(mock_ack, mock_body, mock_client)

    # assertions
    mock_ack.assert_called_once()
