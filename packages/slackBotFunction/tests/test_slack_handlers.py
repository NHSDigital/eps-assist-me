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


def test_middleware_function(mock_env):
    """Test middleware function execution"""
    from app.slack.slack_handlers import setup_handlers

    # Create mock app
    mock_app = Mock()

    # Mock the middleware decorator to capture the function
    middleware_func = None

    def capture_middleware(func):
        nonlocal middleware_func
        middleware_func = func
        return func

    mock_app.middleware = capture_middleware
    mock_app.event = Mock()
    mock_app.action = Mock()

    with patch("app.config.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test the middleware function
    if middleware_func:
        mock_logger = Mock()
        mock_body = {"test": "data"}
        mock_next = Mock(return_value="next_result")

        result = middleware_func(mock_logger, mock_body, mock_next)

        assert result == "next_result"
        mock_next.assert_called_once()


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

    mock_app.middleware = Mock()
    mock_app.event = capture_event
    mock_app.action = Mock()

    with patch("app.config.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test the handler
    if mention_handler:
        mock_ack = Mock()
        mock_event = {"user": "U123", "text": "test"}
        mock_body = {"event_id": "evt123"}

        with patch("app.slack.slack_handlers.is_duplicate_event", return_value=False):
            with patch("app.slack.slack_handlers.trigger_async_processing") as mock_trigger:
                mention_handler(mock_event, mock_ack, mock_body)

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

    mock_app.middleware = Mock()
    mock_app.event = capture_event
    mock_app.action = Mock()

    with patch("app.config.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test feedback message path
    if message_handler:
        mock_ack = Mock()
        mock_event = {"text": "feedback test message", "channel": "C123", "user": "U456"}
        mock_body = {"event_id": "evt123"}

        with patch("app.slack.slack_handlers.handle_feedback_message") as mock_handle:
            message_handler(mock_event, mock_ack, mock_body)

            mock_ack.assert_called_once()
            mock_handle.assert_called_once_with(mock_event, "test-token")


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

    mock_app.middleware = Mock()
    mock_app.event = capture_event
    mock_app.action = Mock()

    with patch("app.config.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test DM processing path
    if message_handler:
        mock_ack = Mock()
        mock_event = {"text": "regular message", "channel_type": "im", "user": "U456"}
        mock_body = {"event_id": "evt123"}

        with patch("app.slack.slack_handlers.is_duplicate_event", return_value=False):
            with patch("app.slack.slack_handlers.trigger_async_processing") as mock_trigger:
                message_handler(mock_event, mock_ack, mock_body)

                mock_ack.assert_called_once()
                mock_trigger.assert_called_once()


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

    mock_app.middleware = Mock()
    mock_app.event = capture_event
    mock_app.action = Mock()

    with patch("app.config.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test non-DM skip
    if message_handler:
        mock_ack = Mock()
        mock_event = {"text": "regular message", "channel_type": "channel"}  # Not "im"
        mock_body = {"event_id": "evt123"}

        with patch("app.slack.slack_handlers.trigger_async_processing") as mock_trigger:
            message_handler(mock_event, mock_ack, mock_body)

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

    mock_app.middleware = Mock()
    mock_app.event = Mock()
    mock_app.action = capture_action

    with patch("app.config.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test the handler
    if yes_handler:
        mock_ack = Mock()
        mock_body = {
            "user": {"id": "U123"},
            "actions": [{"value": "conv-key|test query"}],
            "channel": {"id": "C123"},
            "message": {"ts": "123"},
        }
        mock_client = Mock()

        with patch("app.slack.slack_handlers.store_feedback") as mock_store:
            yes_handler(mock_ack, mock_body, mock_client)

            mock_ack.assert_called_once()
            mock_store.assert_called_once_with("conv-key", "test query", "positive", "U123")
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

    mock_app.middleware = Mock()
    mock_app.event = Mock()
    mock_app.action = capture_action

    with patch("app.config.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test the handler
    if no_handler:
        mock_ack = Mock()
        mock_body = {
            "user": {"id": "U123"},
            "actions": [{"value": "conv-key|test query"}],
            "channel": {"id": "C123"},
            "message": {"ts": "123"},
        }
        mock_client = Mock()

        with patch("app.slack.slack_handlers.store_feedback") as mock_store:
            no_handler(mock_ack, mock_body, mock_client)

            mock_ack.assert_called_once()
            mock_store.assert_called_once_with("conv-key", "test query", "negative", "U123")
            mock_client.chat_postMessage.assert_called_once()


def test_is_duplicate_event_error_handling(mock_env):
    """Test is_duplicate_event error handling"""
    from app.slack.slack_handlers import is_duplicate_event

    with patch("app.config.config.table") as mock_table:
        # Test non-ConditionalCheckFailedException error
        error = ClientError(error_response={"Error": {"Code": "ServiceUnavailable"}}, operation_name="PutItem")
        mock_table.put_item.side_effect = error

        with patch("time.time", return_value=1000):
            result = is_duplicate_event("test-event")

            # Should return False on error to allow processing
            assert result is False


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

    mock_app.middleware = Mock()
    mock_app.event = capture_event
    mock_app.action = Mock()

    with patch("app.config.config.bot_token", "test-token"):
        setup_handlers(mock_app)

    # Test duplicate event handling
    if mention_handler:
        mock_ack = Mock()
        mock_event = {"user": "U123", "text": "test"}
        mock_body = {"event_id": "evt123"}

        with patch("app.slack.slack_handlers.is_duplicate_event", return_value=True):
            with patch("app.slack.slack_handlers.trigger_async_processing") as mock_trigger:
                mention_handler(mock_event, mock_ack, mock_body)

                mock_ack.assert_called_once()
                mock_trigger.assert_not_called()  # Should not trigger for duplicate
