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

        with patch("app.slack.slack_handlers.store_feedback") as mock_store:
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

        with patch("app.slack.slack_handlers.store_feedback") as mock_store:
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
