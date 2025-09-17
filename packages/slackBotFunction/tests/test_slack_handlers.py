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
    mock_app = Mock()
    # Capture the app_mention handler
    mention_handler = None

    def capture_event(event_type):
        def decorator(func):
            nonlocal mention_handler
            if event_type == "app_mention":
                mention_handler = func
            return func

        return decorator

    mock_app.event = capture_event
    mock_app.action = Mock()
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
    from app.slack.slack_handlers import setup_handlers

    # perform operation
    setup_handlers(mock_app)
    mention_handler(mock_event, mock_ack, mock_body, mock_client)

    # assertions
    mock_ack.assert_called_once()
    mock_trigger_async_processing.assert_called_once_with(
        {"event": mock_event, "event_id": "evt123", "bot_token": "test-token"}
    )
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
    mock_app = Mock()
    mock_is_duplicate_event.return_value = False

    # Capture the message handler
    message_handler = None

    def capture_event(event_type):
        def decorator(func):
            nonlocal message_handler
            if event_type == "message":
                message_handler = func
            return func

        return decorator

    mock_app.event = capture_event
    mock_app.action = Mock()
    mock_ack = Mock()
    mock_event = {"text": "regular message", "channel_type": "channel", "channel": "C123"}  # Not "im"
    mock_body = {"event_id": "evt123"}
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import setup_handlers

    # perform operation
    setup_handlers(mock_app)
    # Test non-DM skip
    message_handler(mock_event, mock_ack, mock_body, mock_client)

    # assertions
    mock_ack.assert_called_once()
    mock_trigger_async_processing.assert_not_called()  # Should not trigger for non-DM
    mock_respond_with_eyes.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
def test_feedback_yes_action_handler(
    mock_store_feedback: Mock,
    mock_respond_with_eyes: Mock,
    mock_trigger_async_processing: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback_yes action handler"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import setup_handlers

    mock_app = Mock()

    # Capture the feedback_yes handler
    yes_handler = None

    def capture_action(action_id):
        def decorator(func):
            nonlocal yes_handler
            if action_id == "feedback_yes":
                yes_handler = func
            return func

        return decorator

    mock_app.event = Mock()
    mock_app.action = capture_action

    setup_handlers(mock_app)

    # Test the handler
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

    with patch("app.slack.slack_handlers._is_latest_message", return_value=True):
        yes_handler(mock_ack, mock_body, mock_client)

        mock_ack.assert_called_once()
        mock_store_feedback.assert_called_once_with(
            conversation_key="conv-key",
            feedback_type="positive",
            user_id="U123",
            channel_id="C123",
            thread_ts="123",
            feedback_text="456",
            client=ANY,
        )
        mock_client.chat_postMessage.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
def test_feedback_no_action_handler(
    mock_store_feedback,
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_get_parameter,
    mock_env,
):
    """Test feedback_no action handler"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import setup_handlers

    mock_app = Mock()

    # Capture the feedback_no handler
    no_handler = None

    def capture_action(action_id):
        def decorator(func):
            nonlocal no_handler
            if action_id == "feedback_no":
                no_handler = func
            return func

        return decorator

    mock_app.event = Mock()
    mock_app.action = capture_action

    setup_handlers(mock_app)

    # Test the handler
    mock_ack = Mock()
    mock_body = {
        "user": {"id": "U123"},
        "actions": [
            {"action_id": "feedback_no", "value": '{"ck": "conv-key", "ch": "C123", "tt": "123", "mt": "456"}'}
        ],
        "channel": {"id": "C123"},
        "message": {"ts": "123"},
    }
    mock_client = Mock()

    with patch("app.slack.slack_handlers._is_latest_message", return_value=True):
        no_handler(mock_ack, mock_body, mock_client)

        mock_ack.assert_called_once()
        mock_store_feedback.assert_called_once_with(
            conversation_key="conv-key",
            feedback_type="negative",
            user_id="U123",
            channel_id="C123",
            thread_ts="123",
            feedback_text="456",
            client=ANY,
        )
        mock_client.chat_postMessage.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_duplicate_event_skip_processing(
    mock_respond_with_eyes, mock_trigger_async_processing, mock_is_duplicate_event, mock_get_parameter, mock_env
):
    """Test that duplicate events skip processing"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import setup_handlers

    mock_app = Mock()

    # Capture the app_mention handler
    mention_handler = None

    def capture_event(event_type):
        def decorator(func):
            nonlocal mention_handler
            if event_type == "app_mention":
                mention_handler = func
            return func

        return decorator

    mock_app.event = capture_event
    mock_app.action = Mock()

    setup_handlers(mock_app)

    # Test duplicate event handling
    mock_ack = Mock()
    mock_event = {"user": "U123", "text": "test", "channel": "C123"}
    mock_body = {"event_id": "evt123"}
    mock_client = Mock()
    mock_is_duplicate_event.return_value = True
    mention_handler(mock_event, mock_ack, mock_body, mock_client)

    mock_ack.assert_called_once()
    mock_trigger_async_processing.assert_not_called()  # Should not trigger for duplicate


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
def test_app_mention_feedback_store_feedback_error_handling(
    mock_store_feedback,
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_get_parameter,
    mock_env,
):
    """Test app mention feedback error handling"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    mock_ack = Mock()
    mock_client = Mock()
    mock_event = {"text": "<@U123> feedback: this is feedback", "user": "U456", "channel": "C789", "ts": "123"}
    mock_body = {"event_id": "evt123"}
    mock_is_duplicate_event.return_value = False

    mock_store_feedback.side_effect = Exception("Storage failed")
    mention_handler(mock_event, mock_ack, mock_body, mock_client)
    # Should still try to post message
    mock_client.chat_postMessage.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
def test_app_mention_feedback_post_error_handling(
    mock_store_feedback,
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_get_parameter,
    mock_env,
):
    """Test app mention feedback error handling"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    mock_ack = Mock()
    mock_client = Mock()
    mock_event = {"text": "<@U123> feedback: this is feedback", "user": "U456", "channel": "C789", "ts": "123"}
    mock_body = {"event_id": "evt123"}
    mock_client.chat_postMessage.side_effect = Exception("Post failed")

    mention_handler(mock_event, mock_ack, mock_body, mock_client)
    # Should not raise exception


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
def test_dm_message_handler_feedback_error_handling(
    mock_store_feedback,
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_get_parameter,
    mock_env,
):
    """Test DM message handler feedback error handling"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import dm_message_handler

    mock_client = Mock()
    mock_event = {"text": "feedback: DM feedback", "user": "U456", "channel": "D789", "ts": "123", "channel_type": "im"}

    mock_store_feedback.side_effect = Exception("Storage failed")
    dm_message_handler(mock_event, "evt123", mock_client)
    mock_client.chat_postMessage.assert_called_once()


@patch("app.services.dynamo.get_state_information")
def test_thread_message_handler_session_check_error(mock_get_state_information, mock_get_parameter, mock_env):
    """Test thread_message_handler session check error"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import thread_message_handler

    mock_client = Mock()
    mock_event = {"text": "follow up", "channel": "C789", "thread_ts": "123", "user": "U456"}

    mock_get_state_information.side_effect = Exception("DB error")
    # Should return early due to error
    thread_message_handler(mock_event, "evt123", mock_client)


def test_feedback_handler_unknown_action(mock_env):
    """Test feedback_handler with unknown action"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    mock_ack = Mock()
    mock_body = {"actions": [{"action_id": "unknown_action", "value": "{}"}]}
    mock_client = Mock()

    feedback_handler(mock_ack, mock_body, mock_client)
    mock_ack.assert_called_once()


def test_feedback_handler_not_latest_message(mock_env):
    """Test feedback_handler when not latest message"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    mock_ack = Mock()
    mock_body = {"actions": [{"action_id": "feedback_yes", "value": '{"ck": "conv-key", "mt": "123"}'}]}
    mock_client = Mock()

    with patch("app.slack.slack_handlers._is_latest_message", return_value=False):
        feedback_handler(mock_ack, mock_body, mock_client)
        mock_ack.assert_called_once()


@patch("app.services.dynamo.get_state_information")
def test_thread_message_handler_no_session(mock_get_state_information, mock_env):
    """Test thread_message_handler when no session found"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import thread_message_handler

    mock_client = Mock()
    mock_event = {"text": "follow up", "channel": "C789", "thread_ts": "123", "user": "U456"}

    mock_get_state_information.return_value = {}  # No session
    thread_message_handler(mock_event, "evt123", mock_client)


@patch("app.services.dynamo.get_state_information")
def test_thread_message_handler_feedback_path(mock_get_state_information, mock_env):
    """Test thread_message_handler feedback path"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import thread_message_handler

    mock_client = Mock()
    mock_event = {"text": "feedback: channel feedback", "channel": "C789", "thread_ts": "123", "user": "U456"}

    mock_get_state_information.return_value = {"Item": {"session_id": "session123"}}
    # Just test that the function runs without error
    thread_message_handler(mock_event, "evt123", mock_client)


@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_dm_message_handler_normal_message(
    mock_respond_with_eyes, mock_trigger_async_processing, mock_get_parameter, mock_env
):
    """Test dm_message_handler with normal message"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import dm_message_handler

    mock_client = Mock()
    mock_event = {"text": "normal message", "user": "U456", "channel": "D789", "ts": "123", "channel_type": "im"}

    dm_message_handler(mock_event, "evt123", mock_client)
    mock_trigger_async_processing.assert_called_once()


@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.utils.handler_utils.is_duplicate_event")
def test_mention_handler_normal_mention(
    mock_is_duplicate_event, mock_respond_with_eyes, mock_trigger_async_processing, mock_get_parameter, mock_env
):
    """Test mention_handler with normal mention"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    mock_ack = Mock()
    mock_client = Mock()
    mock_event = {"text": "<@U123> normal question", "user": "U456", "channel": "C789", "ts": "123"}
    mock_body = {"event_id": "evt123"}
    mock_is_duplicate_event.return_value = False

    mention_handler(mock_event, mock_ack, mock_body, mock_client)
    mock_trigger_async_processing.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
def test_feedback_handler_conditional_check_failed(
    mock_store_feedback,
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_get_parameter,
    mock_env,
):
    """Test feedback_handler with ConditionalCheckFailedException"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    mock_ack = Mock()
    mock_body = {
        "user": {"id": "U123"},
        "actions": [{"action_id": "feedback_yes", "value": '{"ck": "conv-key", "mt": "123"}'}],
    }
    mock_client = Mock()

    error = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
    mock_store_feedback.side_effect = error
    with patch("app.slack.slack_handlers._is_latest_message", return_value=True):
        feedback_handler(mock_ack, mock_body, mock_client)
        mock_ack.assert_called_once()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
@patch("app.slack.slack_events.store_feedback")
def test_feedback_handler_storage_error(
    mock_store_feedback,
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_get_parameter,
    mock_env,
):
    """Test feedback_handler with storage error"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    mock_ack = Mock()
    mock_body = {
        "user": {"id": "U123"},
        "actions": [{"action_id": "feedback_yes", "value": '{"ck": "conv-key", "mt": "123"}'}],
    }
    mock_client = Mock()
    mock_store_feedback.side_effect = Exception("Storage error")
    with patch("app.slack.slack_handlers._is_latest_message", return_value=True):
        feedback_handler(mock_ack, mock_body, mock_client)
        mock_ack.assert_called_once()


@patch("app.services.dynamo.get_state_information")
def test_is_latest_message_matching_ts(mock_get_state_information):
    """Test _is_latest_message function logic"""

    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import _is_latest_message

    mock_get_state_information.return_value = {"Item": {"latest_message_ts": "123"}}
    assert _is_latest_message("conv-key", "123") is True


@patch("app.services.dynamo.get_state_information")
def test_is_latest_message_non_matching_ts(mock_get_state_information):
    """Test _is_latest_message function logic"""

    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import _is_latest_message

    mock_get_state_information.return_value = {"Item": {"latest_message_ts": "456"}}
    assert _is_latest_message("conv-key", "123") is False


@patch("app.services.dynamo.get_state_information")
def test_is_latest_message_no_item_in_response(mock_get_state_information):
    """Test _is_latest_message function logic"""

    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import _is_latest_message

    mock_get_state_information.return_value = {}
    assert _is_latest_message("conv-key", "123") is False


@patch("app.services.dynamo.get_state_information")
def test_is_latest_message_exception(mock_get_state_information):
    """Test _is_latest_message function logic"""

    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import _is_latest_message

    mock_get_state_information.side_effect = Exception("DB error")
    assert _is_latest_message("conv-key", "123") is False


def test_gate_common_missing_event_id(mock_env):
    """Test _gate_common with missing event_id"""
    from app.slack.slack_handlers import _gate_common

    event = {"text": "test"}
    body = {}  # Missing event_id

    result = _gate_common(event, body)
    assert result is None


def test_gate_common_bot_message(mock_env):
    """Test _gate_common with bot message"""
    from app.slack.slack_handlers import _gate_common

    event = {"text": "test", "bot_id": "B123"}
    body = {"event_id": "evt123"}

    result = _gate_common(event, body)
    assert result is None


def test_gate_common_subtype_message(mock_env):
    """Test _gate_common with subtype message"""
    from app.slack.slack_handlers import _gate_common

    event = {"text": "test", "subtype": "message_changed"}
    body = {"event_id": "evt123"}

    result = _gate_common(event, body)
    assert result is None


def test_strip_mentions_with_alias(mock_env):
    """Test _strip_mentions with user alias"""
    from app.slack.slack_handlers import _strip_mentions

    text = "<@U123|username> hello world"
    result = _strip_mentions(text)
    assert result == "hello world"
