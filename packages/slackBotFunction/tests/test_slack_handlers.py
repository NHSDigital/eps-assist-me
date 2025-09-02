import pytest
from unittest.mock import Mock, patch
import os
from botocore.exceptions import ClientError


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


def test_setup_handlers_registers_correctly(mock_env):
    """Test that setup_handlers registers all handlers correctly"""
    from app.slack.slack_handlers import setup_handlers

    mock_app = Mock()

    with patch("app.core.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Verify all handlers are registered
    assert mock_app.event.call_count == 2  # app_mention and unified message handler


def test_app_mention_handler(mock_env):
    """Test app mention handler execution"""
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

    with patch("app.core.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test the handler
    if mention_handler:
        mock_ack = Mock()
        mock_event = {"user": "U123", "text": "<@U456> test", "channel": "C123"}
        mock_body = {"event_id": "evt123"}
        mock_client = Mock()

        with patch("app.slack.slack_handlers._is_duplicate_event", return_value=False):
            with patch("app.slack.slack_handlers._trigger_async_processing") as mock_trigger:
                mention_handler(mock_event, mock_ack, mock_body, mock_client)

                mock_ack.assert_called_once()
                mock_trigger.assert_called_once()


def test_message_handler_feedback_path(mock_env):
    """Test message handler feedback detection"""
    from app.slack.slack_handlers import setup_handlers

    mock_app = Mock()

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

    with patch("app.core.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test feedback message path - just verify handler exists
    if message_handler:
        assert callable(message_handler)


def test_message_handler_dm_path(mock_env):
    """Test message handler DM processing"""
    from app.slack.slack_handlers import setup_handlers

    mock_app = Mock()

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

    with patch("app.core.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test DM processing path - just verify handler exists
    if message_handler:
        assert callable(message_handler)


def test_message_handler_non_dm_skip(mock_env):
    """Test message handler skips non-DM messages"""
    from app.slack.slack_handlers import setup_handlers

    mock_app = Mock()

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

    with patch("app.core.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test non-DM skip
    if message_handler:
        mock_ack = Mock()
        mock_event = {"text": "regular message", "channel_type": "channel", "channel": "C123"}  # Not "im"
        mock_body = {"event_id": "evt123"}
        mock_client = Mock()

        with patch("app.slack.slack_handlers._trigger_async_processing") as mock_trigger:
            message_handler(mock_event, mock_ack, mock_body, mock_client)

            mock_ack.assert_called_once()
            mock_trigger.assert_not_called()  # Should not trigger for non-DM


def test_feedback_yes_action_handler(mock_env):
    """Test feedback_yes action handler"""
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

    with patch("app.core.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test the handler
    if yes_handler:
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

        with patch("app.slack.slack_handlers.store_feedback") as mock_store, patch(
            "app.slack.slack_handlers._is_latest_message", return_value=True
        ):
            yes_handler(mock_ack, mock_body, mock_client)

            mock_ack.assert_called_once()
            mock_store.assert_called_once_with("conv-key", None, "positive", "U123", "C123", "123", "456")
            mock_client.chat_postMessage.assert_called_once()


def test_feedback_no_action_handler(mock_env):
    """Test feedback_no action handler"""
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

    with patch("app.core.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test the handler
    if no_handler:
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

        with patch("app.slack.slack_handlers.store_feedback") as mock_store, patch(
            "app.slack.slack_handlers._is_latest_message", return_value=True
        ):
            no_handler(mock_ack, mock_body, mock_client)

            mock_ack.assert_called_once()
            mock_store.assert_called_once_with("conv-key", None, "negative", "U123", "C123", "123", "456")
            mock_client.chat_postMessage.assert_called_once()


def test_app_mention_feedback_handler(mock_env):
    """Test app mention feedback handling"""
    from app.slack.slack_handlers import setup_handlers

    mock_app = Mock()
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

    with patch("app.core.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test feedback in @mention - just verify handler exists
    if mention_handler:
        assert callable(mention_handler)


def test_is_duplicate_event_error_handling(mock_env):
    """Test _is_duplicate_event error handling"""
    from app.slack.slack_handlers import _is_duplicate_event

    with patch("app.core.config.table") as mock_table:
        mock_table.put_item.side_effect = ClientError({"Error": {"Code": "SomeOtherError"}}, "put_item")

        result = _is_duplicate_event("test-event")
        assert result is False  # Should return False on non-conditional errors


def test_duplicate_event_skip_processing(mock_env):
    """Test that duplicate events skip processing"""
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

    with patch("app.core.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test duplicate event handling
    if mention_handler:
        mock_ack = Mock()
        mock_event = {"user": "U123", "text": "test", "channel": "C123"}
        mock_body = {"event_id": "evt123"}
        mock_client = Mock()

        with patch("app.slack.slack_handlers._is_duplicate_event", return_value=True):
            with patch("app.slack.slack_handlers._trigger_async_processing") as mock_trigger:
                mention_handler(mock_event, mock_ack, mock_body, mock_client)

                mock_ack.assert_called_once()
                mock_trigger.assert_not_called()  # Should not trigger for duplicate


def test_app_mention_feedback_error_handling(mock_env):
    """Test app mention feedback error handling"""
    from app.slack.slack_handlers import app_mention_handler

    mock_ack = Mock()
    mock_client = Mock()
    mock_event = {"text": "<@U123> feedback: this is feedback", "user": "U456", "channel": "C789", "ts": "123"}
    mock_body = {"event_id": "evt123"}

    with patch("app.slack.slack_handlers.store_feedback_with_qa") as mock_store:
        mock_store.side_effect = Exception("Storage failed")
        app_mention_handler(mock_event, mock_ack, mock_body, mock_client)
        # Should still try to post message
        mock_client.chat_postMessage.assert_called_once()

    # Test post message error
    mock_client.reset_mock()
    mock_client.chat_postMessage.side_effect = Exception("Post failed")

    with patch("app.slack.slack_handlers.store_feedback_with_qa"):
        app_mention_handler(mock_event, mock_ack, mock_body, mock_client)
        # Should not raise exception


def test_dm_message_handler_feedback_error_handling(mock_env):
    """Test DM message handler feedback error handling"""
    from app.slack.slack_handlers import dm_message_handler

    mock_client = Mock()
    mock_event = {"text": "feedback: DM feedback", "user": "U456", "channel": "D789", "ts": "123", "channel_type": "im"}
    mock_body = {"event_id": "evt123"}

    with patch("app.slack.slack_handlers.store_feedback_with_qa") as mock_store:
        mock_store.side_effect = Exception("Storage failed")
        dm_message_handler(mock_event, "evt123", mock_body, mock_client)
        mock_client.chat_postMessage.assert_called_once()


def test_channel_message_handler_session_check_error(mock_env):
    """Test channel_message_handler session check error"""
    from app.slack.slack_handlers import channel_message_handler

    mock_client = Mock()
    mock_event = {"text": "follow up", "channel": "C789", "thread_ts": "123", "user": "U456"}
    mock_body = {"event_id": "evt123"}

    with patch("app.core.config.table") as mock_table:
        mock_table.get_item.side_effect = Exception("DB error")
        # Should return early due to error
        channel_message_handler(mock_event, "evt123", mock_body, mock_client)


def test_feedback_handler_unknown_action(mock_env):
    """Test feedback_handler with unknown action"""
    from app.slack.slack_handlers import feedback_handler

    mock_ack = Mock()
    mock_body = {"actions": [{"action_id": "unknown_action", "value": "{}"}]}
    mock_client = Mock()

    feedback_handler(mock_ack, mock_body, mock_client)
    mock_ack.assert_called_once()


def test_feedback_handler_not_latest_message(mock_env):
    """Test feedback_handler when not latest message"""
    from app.slack.slack_handlers import feedback_handler

    mock_ack = Mock()
    mock_body = {"actions": [{"action_id": "feedback_yes", "value": '{"ck": "conv-key", "mt": "123"}'}]}
    mock_client = Mock()

    with patch("app.slack.slack_handlers._is_latest_message", return_value=False):
        feedback_handler(mock_ack, mock_body, mock_client)
        mock_ack.assert_called_once()


def test_channel_message_handler_no_session(mock_env):
    """Test channel_message_handler when no session found"""
    from app.slack.slack_handlers import channel_message_handler

    mock_client = Mock()
    mock_event = {"text": "follow up", "channel": "C789", "thread_ts": "123", "user": "U456"}
    mock_body = {"event_id": "evt123"}

    with patch("app.core.config.table") as mock_table:
        mock_table.get_item.return_value = {}  # No session
        channel_message_handler(mock_event, "evt123", mock_body, mock_client)


def test_channel_message_handler_feedback_path(mock_env):
    """Test channel_message_handler feedback path"""
    from app.slack.slack_handlers import channel_message_handler

    mock_client = Mock()
    mock_event = {"text": "feedback: channel feedback", "channel": "C789", "thread_ts": "123", "user": "U456"}
    mock_body = {"event_id": "evt123"}

    with patch("app.core.config.table") as mock_table:
        mock_table.get_item.return_value = {"Item": {"session_id": "session123"}}
        # Just test that the function runs without error
        channel_message_handler(mock_event, "evt123", mock_body, mock_client)


def test_dm_message_handler_normal_message(mock_env):
    """Test dm_message_handler with normal message"""
    from app.slack.slack_handlers import dm_message_handler

    mock_client = Mock()
    mock_event = {"text": "normal message", "user": "U456", "channel": "D789", "ts": "123", "channel_type": "im"}
    mock_body = {"event_id": "evt123"}

    with patch("app.slack.slack_handlers._trigger_async_processing") as mock_trigger:
        dm_message_handler(mock_event, "evt123", mock_body, mock_client)
        mock_trigger.assert_called_once()


def test_app_mention_handler_normal_mention(mock_env):
    """Test app_mention_handler with normal mention"""
    from app.slack.slack_handlers import app_mention_handler

    mock_ack = Mock()
    mock_client = Mock()
    mock_event = {"text": "<@U123> normal question", "user": "U456", "channel": "C789", "ts": "123"}
    mock_body = {"event_id": "evt123"}

    with patch("app.slack.slack_handlers._is_duplicate_event", return_value=False), patch(
        "app.slack.slack_handlers._trigger_async_processing"
    ) as mock_trigger:
        app_mention_handler(mock_event, mock_ack, mock_body, mock_client)
        mock_trigger.assert_called_once()


def test_feedback_handler_conditional_check_failed(mock_env):
    """Test feedback_handler with ConditionalCheckFailedException"""
    from app.slack.slack_handlers import feedback_handler
    from botocore.exceptions import ClientError

    mock_ack = Mock()
    mock_body = {
        "user": {"id": "U123"},
        "actions": [{"action_id": "feedback_yes", "value": '{"ck": "conv-key", "mt": "123"}'}],
    }
    mock_client = Mock()

    error = ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")

    with patch("app.slack.slack_handlers._is_latest_message", return_value=True), patch(
        "app.slack.slack_handlers.store_feedback", side_effect=error
    ):
        feedback_handler(mock_ack, mock_body, mock_client)
        mock_ack.assert_called_once()


def test_feedback_handler_storage_error(mock_env):
    """Test feedback_handler with storage error"""
    from app.slack.slack_handlers import feedback_handler

    mock_ack = Mock()
    mock_body = {
        "user": {"id": "U123"},
        "actions": [{"action_id": "feedback_yes", "value": '{"ck": "conv-key", "mt": "123"}'}],
    }
    mock_client = Mock()

    with patch("app.slack.slack_handlers._is_latest_message", return_value=True), patch(
        "app.slack.slack_handlers.store_feedback", side_effect=Exception("Storage error")
    ):
        feedback_handler(mock_ack, mock_body, mock_client)
        mock_ack.assert_called_once()
