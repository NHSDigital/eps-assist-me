import sys
from unittest.mock import ANY, Mock, patch
from botocore.exceptions import ClientError
from app.core.config import (
    bot_messages,
)


# mention handler
@patch("app.utils.handler_utils.is_duplicate_event")
def test_mention_handler_successful_call(
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test app mention handler execution"""
    # set up mocks
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
    with patch("app.slack.slack_handlers._common_message_handler") as mock_common_message_handler:
        mention_handler(event=mock_event, body=mock_body, client=mock_client)

        # assertions
        mock_common_message_handler.assert_called_once_with(
            message_text="test",
            conversation_key="thread#C123#123",
            thread_root="123",
            client=ANY,
            event=mock_event,
            event_id="evt123",
            post_to_thread=True,
        )


@patch("app.utils.handler_utils.is_duplicate_event")
def test_mention_handler_duplicate_event_duplicate_event(
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test that duplicate events skip processing"""
    # setup mocks
    mock_event = {"user": "U123", "text": "test", "channel": "C123"}
    mock_body = {"event_id": "evt123"}
    mock_client = Mock()
    mock_is_duplicate_event.return_value = True

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    # perform operation
    with patch("app.slack.slack_handlers._common_message_handler") as mock_common_message_handler:
        mention_handler(event=mock_event, body=mock_body, client=mock_client)

        # assertions
        mock_common_message_handler.assert_not_called()


@patch("app.utils.handler_utils.is_duplicate_event")
def test_mention_handler_bot_event(
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test that duplicate events skip processing"""
    # setup mocks
    mock_event = {"bot_id": "U123", "text": "test", "channel": "C123"}
    mock_body = {"event_id": "evt123"}
    mock_client = Mock()
    mock_is_duplicate_event.return_value = False

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    # perform operation
    with patch("app.slack.slack_handlers._common_message_handler") as mock_common_message_handler:
        mention_handler(event=mock_event, body=mock_body, client=mock_client)

        # assertions
        mock_common_message_handler.assert_not_called()
        mock_is_duplicate_event.assert_not_called()


@patch("app.utils.handler_utils.is_duplicate_event")
def test_mention_handler_subtype_event(
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test that duplicate events skip processing"""
    # setup mocks
    mock_event = {"subtype": "foo", "user_id": "U123", "text": "test", "channel": "C123"}
    mock_body = {"event_id": "evt123"}
    mock_client = Mock()
    mock_is_duplicate_event.return_value = False

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    # perform operation
    with patch("app.slack.slack_handlers._common_message_handler") as mock_common_message_handler:
        mention_handler(event=mock_event, body=mock_body, client=mock_client)

        # assertions
        mock_common_message_handler.assert_not_called()
        mock_is_duplicate_event.assert_not_called()


@patch("app.utils.handler_utils.is_duplicate_event")
def test_mention_handler_missing_event_id(
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test that duplicate events skip processing"""
    # setup mocks
    mock_event = {"user_id": "U123", "text": "test", "channel": "C123"}
    mock_body = {}
    mock_client = Mock()
    mock_is_duplicate_event.return_value = False

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import mention_handler

    # perform operation
    with patch("app.slack.slack_handlers._common_message_handler") as mock_common_message_handler:
        mention_handler(event=mock_event, body=mock_body, client=mock_client)

        # assertions
        mock_common_message_handler.assert_not_called()
        mock_is_duplicate_event.assert_not_called()


# unified_message_handler
@patch("app.utils.handler_utils.is_duplicate_event")
def test_unified_message_handler_handles_dm_messages(
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test message handler skips non-DM messages"""
    # set up mocks
    mock_is_duplicate_event.return_value = False
    mock_event = {"text": "regular message", "channel_type": "im", "channel": "im"}
    mock_body = {"event_id": "evt123"}
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import unified_message_handler

    with patch("app.slack.slack_handlers.dm_message_handler") as mock_dm_message_handler, patch(
        "app.slack.slack_handlers.thread_message_handler"
    ) as mock_thread_message_handler:
        unified_message_handler(event=mock_event, body=mock_body, client=mock_client)

        # assertions
        mock_thread_message_handler.assert_not_called()
        mock_dm_message_handler.assert_called_with(event=mock_event, event_id="evt123", client=ANY)


@patch("app.utils.handler_utils.is_duplicate_event")
def test_unified_message_handler_handles_threadable_messages(
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test message handler skips non-DM messages"""
    # set up mocks
    mock_is_duplicate_event.return_value = False
    mock_event = {"text": "regular message", "channel_type": "channel", "channel": "C123"}  # Not "im"
    mock_body = {"event_id": "evt123"}
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import unified_message_handler

    with patch("app.slack.slack_handlers.dm_message_handler") as mock_dm_message_handler, patch(
        "app.slack.slack_handlers.thread_message_handler"
    ) as mock_thread_message_handler:
        unified_message_handler(event=mock_event, body=mock_body, client=mock_client)

        # assertions
        mock_dm_message_handler.assert_not_called()
        mock_thread_message_handler.assert_called_with(event=mock_event, event_id="evt123", client=ANY)


# _common_message_handler
@patch("app.slack.slack_events.store_feedback")
@patch("app.services.slack.post_error_message")
def test_common_message_handler_store_feedback_error_handling(
    mock_post_error_message: Mock,
    mock_store_feedback: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback error handling - failed to store feedback"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "feedback: this is feedback", "user": "U456", "channel": "C789", "ts": "123"}

    mock_store_feedback.side_effect = Exception("Storage failed")

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _common_message_handler

    # perform operation
    _common_message_handler(
        message_text="feedback: this is feedback",
        conversation_key="foo",
        thread_root="bar",
        client=mock_client,
        event=mock_event,
        event_id="evt123",
        post_to_thread=True,
    )

    # assertions
    # Should still try to post message
    mock_client.chat_postMessage.assert_called_once_with(
        channel="C789", text=bot_messages.FEEDBACK_THANKS, thread_ts="bar"
    )
    mock_post_error_message.assert_not_called()


@patch("app.slack.slack_events.store_feedback")
@patch("app.services.slack.post_error_message")
def test_common_message_handler_feedback_post_message_error_handling(
    mock_post_error_message: Mock,
    mock_store_feedback: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test DM message handler feedback error handling"""
    # setup mocks
    mock_client = Mock()
    mock_event = {
        "text": "feedback: DM feedback",
        "user": "U456",
        "channel": "D789",
        "ts": "123",
        "channel_type": "not_im",
    }
    mock_client.chat_postMessage.side_effect = Exception("Post failed")

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _common_message_handler

    # perform operation
    _common_message_handler(
        message_text="feedback: this is feedback",
        conversation_key="foo",
        thread_root="123",
        client=mock_client,
        event=mock_event,
        event_id="evt123",
        post_to_thread=True,
    )

    # assertions
    # we just want to check it does not throw an error
    mock_client.chat_postMessage.assert_called_once()
    mock_post_error_message.assert_called_once_with(channel="D789", thread_ts="123", client=mock_client)


@patch("app.slack.slack_events.store_feedback")
@patch("app.services.slack.post_error_message")
def test_common_message_handler_store_feedback_success(
    mock_post_error_message: Mock,
    mock_store_feedback: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback success"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "feedback: this is feedback", "user": "U456", "channel": "C789", "ts": "123"}

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _common_message_handler

    # perform operation
    _common_message_handler(
        message_text="feedback: this is feedback",
        conversation_key="foo",
        thread_root="bar",
        client=mock_client,
        event=mock_event,
        event_id="evt123",
        post_to_thread=True,
    )

    # assertions
    # Should still try to post message
    mock_client.chat_postMessage.assert_called_once_with(
        channel="C789", text=bot_messages.FEEDBACK_THANKS, thread_ts="bar"
    )
    mock_post_error_message.assert_not_called()


@patch("app.utils.handler_utils.trigger_pull_request_processing")
@patch("app.services.slack.post_error_message")
def test_common_message_handler_pull_request_success(
    mock_post_error_message: Mock,
    mock_trigger_pull_request_processing: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test pull request handling"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "feedback: this is feedback", "user": "U456", "channel": "C789", "ts": "123"}

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _common_message_handler

    # perform operation
    _common_message_handler(
        message_text="pr: 123 this is calling a pull request",
        conversation_key="foo",
        thread_root="bar",
        client=mock_client,
        event=mock_event,
        event_id="evt123",
        post_to_thread=True,
    )

    # assertions
    # Should still try to post
    mock_trigger_pull_request_processing.assert_called_with(pull_request_id=123, event=mock_event, event_id="evt123")
    mock_post_error_message.assert_not_called()
    mock_client.chat_postMessage.assert_not_called()


@patch("app.utils.handler_utils.trigger_pull_request_processing")
@patch("app.services.slack.post_error_message")
def test_common_message_handler_pull_request_success_error_handling(
    mock_post_error_message: Mock,
    mock_trigger_pull_request_processing: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test DM message handler feedback error handling"""
    # setup mocks
    mock_client = Mock()
    mock_event = {
        "text": "feedback: DM feedback",
        "user": "U456",
        "channel": "D789",
        "ts": "123",
        "channel_type": "not_im",
    }
    mock_trigger_pull_request_processing.side_effect = Exception("Trigger failed")

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _common_message_handler

    # perform operation
    _common_message_handler(
        message_text="pr: 123 this is calling a pull request",
        conversation_key="foo",
        thread_root="123",
        client=mock_client,
        event=mock_event,
        event_id="evt123",
        post_to_thread=True,
    )

    # assertions
    # we just want to check it does not throw an error
    mock_client.chat_postMessage.assert_not_called()
    mock_post_error_message.assert_called_once_with(channel="D789", thread_ts="123", client=mock_client)


@patch("app.utils.handler_utils.trigger_pull_request_processing")
@patch("app.services.slack.post_error_message")
@patch("app.slack.slack_events.process_async_slack_event")
def test_common_message_handler_normal_message_success(
    mock_process_async_slack_event: Mock,
    mock_post_error_message: Mock,
    mock_trigger_pull_request_processing: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test pull request handling"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "feedback: this is feedback", "user": "U456", "channel": "C789", "ts": "123"}

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _common_message_handler

    # perform operation
    _common_message_handler(
        message_text="this is a normal message",
        conversation_key="foo",
        thread_root="bar",
        client=mock_client,
        event=mock_event,
        event_id="evt123",
        post_to_thread=True,
    )

    # assertions
    # Should still try to post
    mock_trigger_pull_request_processing.assert_not_called()
    mock_post_error_message.assert_not_called()
    mock_client.chat_postMessage.assert_not_called()
    mock_process_async_slack_event.assert_called_with(event=mock_event, event_id="evt123", client=mock_client)


@patch("app.utils.handler_utils.trigger_pull_request_processing")
@patch("app.services.slack.post_error_message")
@patch("app.slack.slack_events.process_async_slack_event")
def test_common_message_handler_normal_message_error_handling(
    mock_process_async_slack_event: Mock,
    mock_post_error_message: Mock,
    mock_trigger_pull_request_processing: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test pull request handling"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "feedback: this is feedback", "user": "U456", "channel": "C789", "ts": "123"}
    mock_process_async_slack_event.side_effect = Exception("Process failed")

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import _common_message_handler

    # perform operation
    _common_message_handler(
        message_text="this is a normal message",
        conversation_key="foo",
        thread_root="bar",
        client=mock_client,
        event=mock_event,
        event_id="evt123",
        post_to_thread=True,
    )

    # assertions
    # Should still try to post
    mock_trigger_pull_request_processing.assert_not_called()
    mock_post_error_message.assert_not_called()
    mock_client.chat_postMessage.assert_not_called()


# thread message handler
@patch("app.services.dynamo.get_state_information")
@patch("app.services.slack.post_error_message")
def test_thread_message_handler_session_check_error(
    mock_post_error_message: Mock, mock_get_state_information: Mock, mock_get_parameter: Mock, mock_env: Mock
):
    """Test thread_message_handler session check error"""
    # setup mocks
    mock_client = Mock()
    mock_event = {
        "text": "follow up",
        "channel": "C789",
        "channel_type": "not_im",
        "thread_ts": "123",
        "ts": "evt_ts",
        "user": "U456",
    }

    mock_get_state_information.side_effect = Exception("DB error")

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import thread_message_handler

    # perform operation
    # Should return early due to error
    with patch("app.slack.slack_handlers._common_message_handler") as mock_common_message_handler:
        thread_message_handler(event=mock_event, event_id="evt123", client=mock_client)

        # assertions
        mock_common_message_handler.assert_not_called()
        mock_post_error_message.assert_called_once_with(channel="C789", thread_ts="123", client=mock_client)


@patch("app.services.dynamo.get_state_information")
@patch("app.services.slack.post_error_message")
def test_thread_message_handler_no_session(
    mock_post_error_message: Mock, mock_get_state_information: Mock, mock_env: Mock
):
    """Test thread_message_handler when no session found"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "follow up", "channel": "C789", "thread_ts": "123", "user": "U456"}

    mock_get_state_information.return_value = {}  # No session

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import thread_message_handler

    # perform operation
    with patch("app.slack.slack_handlers._common_message_handler") as mock_common_message_handler:
        thread_message_handler(event=mock_event, event_id="evt123", client=mock_client)

        # assertions
        mock_common_message_handler.assert_not_called()
        mock_post_error_message.assert_not_called()


@patch("app.services.dynamo.get_state_information")
def test_thread_message_handler_success(mock_get_state_information: Mock, mock_env: Mock):
    """Test thread_message_handler success"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "feedback: channel feedback", "channel": "C789", "thread_ts": "123", "user": "U456"}

    mock_get_state_information.return_value = {"Item": {"session_id": "session123"}}

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import thread_message_handler

    # perform operation
    with patch("app.slack.slack_handlers._common_message_handler") as mock_common_message_handler:
        thread_message_handler(event=mock_event, event_id="evt123", client=mock_client)
        # assertions
        mock_common_message_handler.assert_called_once_with(
            message_text="feedback: channel feedback",
            conversation_key="thread#C789#123",
            thread_root="123",
            client=ANY,
            event=mock_event,
            event_id="evt123",
            post_to_thread=True,
        )


# feedback action handler
@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.is_latest_message")
@patch("app.slack.slack_events.store_feedback")
def test_feedback_action_handler_positive_success(
    mock_store_feedback: Mock,
    mock_is_latest_message: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback_yes action handler"""
    # setup mocks
    mock_is_latest_message.return_value = True

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
    feedback_handler(body=mock_body, client=mock_client)

    # assertions
    mock_store_feedback.assert_called_once_with(
        conversation_key="conv-key",
        feedback_type="positive",
        user_id="U123",
        channel_id="C123",
        thread_ts="123",
        message_ts="456",
        client=ANY,
    )
    mock_client.chat_postMessage.assert_called_once_with(
        channel="C123", text=bot_messages.FEEDBACK_POSITIVE_THANKS, thread_ts="123"
    )


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.is_latest_message")
@patch("app.slack.slack_events.store_feedback")
def test_feedback_action_handler_negative_success(
    mock_store_feedback: Mock,
    mock_is_latest_message: Mock,
    mock_is_duplicate_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback_yes action handler"""
    # setup mocks
    mock_is_latest_message.return_value = True

    mock_body = {
        "user": {"id": "U123"},
        "actions": [
            {"action_id": "feedback_no", "value": '{"ck": "conv-key", "ch": "C123", "tt": "123", "mt": "456"}'}
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
    feedback_handler(body=mock_body, client=mock_client)

    # assertions
    mock_store_feedback.assert_called_once_with(
        conversation_key="conv-key",
        feedback_type="negative",
        user_id="U123",
        channel_id="C123",
        thread_ts="123",
        message_ts="456",
        client=ANY,
    )
    mock_client.chat_postMessage.assert_called_once_with(
        channel="C123", text=bot_messages.FEEDBACK_NEGATIVE_THANKS, thread_ts="123"
    )


@patch("app.utils.handler_utils.is_latest_message")
@patch("app.slack.slack_events.store_feedback")
@patch("app.services.slack.post_error_message")
def test_feedback_handler_unknown_action(
    mock_post_error_message: Mock, mock_store_feedback: Mock, mock_is_latest_message: Mock, mock_env: Mock
):
    """Test feedback_handler with unknown action"""
    # setup mocks
    mock_body = {
        "user": {"id": "U123"},
        "actions": [
            {"action_id": "unknown_action", "value": '{"ck": "conv-key", "ch": "C123", "tt": "123", "mt": "456"}'}
        ],
        "channel": {"id": "C123"},
        "message": {"ts": "123"},
    }
    mock_client = Mock()
    mock_is_latest_message.return_value = True

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    # perform operation
    feedback_handler(body=mock_body, client=mock_client)

    # assertions
    mock_store_feedback.assert_not_called()
    mock_post_error_message.assert_not_called()


@patch("app.utils.handler_utils.is_latest_message")
@patch("app.slack.slack_events.store_feedback")
def test_feedback_handler_not_latest_message(mock_store_feedback: Mock, mock_is_latest_message: Mock, mock_env: Mock):
    """Test feedback_handler when not latest message"""
    # setup mocks
    mock_body = {"actions": [{"action_id": "feedback_yes", "value": '{"ck": "conv-key", "mt": "123"}'}]}
    mock_client = Mock()
    mock_is_latest_message.return_value = False

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    # perform operation
    feedback_handler(body=mock_body, client=mock_client)

    # assertions
    mock_store_feedback.assert_not_called()


@patch("app.slack.slack_events.store_feedback")
@patch("app.utils.handler_utils.is_latest_message")
@patch("app.services.slack.post_error_message")
def test_feedback_handler_conditional_check_failed(
    mock_post_error_message: Mock,
    mock_is_latest_message: Mock,
    mock_store_feedback: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback_handler with ConditionalCheckFailedException"""
    # setup mocks
    mock_is_latest_message.return_value = True
    mock_body = {
        "user": {"id": "U123"},
        "actions": [
            {"action_id": "feedback_no", "value": '{"ck": "conv-key", "ch": "C123", "tt": "123", "mt": "456"}'}
        ],
        "channel": {"id": "C123"},
        "message": {"ts": "123"},
    }
    mock_client = Mock()

    error = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
    mock_store_feedback.side_effect = error

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    # perform operation
    feedback_handler(body=mock_body, client=mock_client)

    # assertions
    mock_post_error_message.assert_not_called()


@patch("app.slack.slack_events.store_feedback")
@patch("app.utils.handler_utils.is_latest_message")
@patch("app.services.slack.post_error_message")
def test_feedback_handler_storage_error(
    mock_post_error_message: Mock,
    mock_is_latest_message: Mock,
    mock_store_feedback: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback_handler with storage error"""
    # setup mocks
    mock_is_latest_message.return_value = True
    mock_body = {
        "user": {"id": "U123"},
        "actions": [
            {"action_id": "feedback_no", "value": '{"ck": "conv-key", "ch": "C123", "tt": "123", "mt": "456"}'}
        ],
        "channel": {"id": "C123"},
        "message": {"ts": "123"},
    }
    mock_client = Mock()
    mock_store_feedback.side_effect = Exception("Storage error")

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    # perform operation
    feedback_handler(body=mock_body, client=mock_client)

    # assertions
    mock_post_error_message.assert_called_once_with(channel="C123", thread_ts="123", client=mock_client)


@patch("app.utils.handler_utils.is_latest_message")
@patch("app.services.slack.post_error_message")
def test_feedback_handler_general_error(
    mock_post_error_message: Mock,
    mock_is_latest_message: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback_handler with storage error"""
    # setup mocks
    mock_is_latest_message.return_value = True
    mock_body = {
        "user": {"id": "U123"},
        "channel": {"id": "C123"},
        "message": {"ts": "123"},
    }
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    # perform operation
    feedback_handler(body=mock_body, client=mock_client)

    # assertions
    mock_post_error_message.assert_not_called()


# dm_message_handler
def test_dm_message_handler_success(mock_get_parameter: Mock, mock_env: Mock):
    """Test dm_message_handler with normal message"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "dm message", "user": "U456", "channel": "D789", "ts": "123", "channel_type": "im"}

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import dm_message_handler

    # perform operation
    with patch("app.slack.slack_handlers._common_message_handler") as mock_common_message_handler:
        dm_message_handler(event=mock_event, event_id="evt123", client=mock_client)

        # assertions
        mock_common_message_handler.assert_called_once_with(
            message_text="dm message",
            conversation_key="dm#D789",
            thread_root="123",
            client=ANY,
            event=mock_event,
            event_id="evt123",
            post_to_thread=False,
        )


def test_dm_message_handler_not_a_dm(mock_get_parameter: Mock, mock_env: Mock):
    """Test dm_message_handler with normal message"""
    # setup mocks
    mock_client = Mock()
    mock_event = {"text": "dm message", "user": "U456", "channel": "im", "ts": "123", "channel_type": "not_im"}

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import dm_message_handler

    # perform operation
    with patch("app.slack.slack_handlers._common_message_handler") as mock_common_message_handler:
        dm_message_handler(event=mock_event, event_id="evt123", client=mock_client)

        # assertions
        mock_common_message_handler.assert_not_called()
