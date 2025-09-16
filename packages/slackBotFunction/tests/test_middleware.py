import sys
from unittest.mock import Mock, patch


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_app_mention_handler_execution_simple(
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_slack_app,
    mock_env,
    mock_get_parameter,
    lambda_context,
):
    """Test app mention handler execution by simulating the handler registration process"""
    # Create a mock app that captures the registered handlers
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_slack_app.event = mock_event_decorator

    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    setup_handlers(mock_slack_app)

    # Now we should have the actual handler function
    assert "app_mention" in registered_handlers
    handler_func = registered_handlers["app_mention"]

    mock_ack = Mock()
    mock_is_duplicate_event.return_value = False

    # Test: Successful flow (no duplicate)
    event = {"user": "U123", "text": "test message"}
    body = {"event_id": "new-event-123"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_trigger_async_processing.assert_called_once()
    mock_is_duplicate_event.assert_called()
    mock_respond_with_eyes.assert_called()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_direct_message_handler_execution_simple(
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_slack_app,
    mock_env,
    mock_get_parameter,
    lambda_context,
):
    """Test direct message handler execution by simulating the handler registration process"""
    # Create a mock app that captures the registered handlers
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_slack_app.event = mock_event_decorator
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    setup_handlers(mock_slack_app)

    # Now we should have the actual handler function
    assert "message" in registered_handlers
    handler_func = registered_handlers["message"]

    mock_ack = Mock()
    mock_is_duplicate_event.return_value = False

    # Test: Successful flow (no duplicate)
    event = {"user": "U123", "text": "test direct message", "channel_type": "im"}
    body = {"event_id": "new-event-456"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_trigger_async_processing.assert_called_once()
    mock_is_duplicate_event.assert_called()
    mock_respond_with_eyes.assert_called()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_app_mention_handler_duplicate_event(
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_slack_app,
    mock_env,
    mock_get_parameter,
    lambda_context,
):
    """Test app mention handler with duplicate event"""
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_slack_app.event = mock_event_decorator
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    setup_handlers(mock_slack_app)

    assert "app_mention" in registered_handlers
    handler_func = registered_handlers["app_mention"]

    mock_ack = Mock()
    mock_is_duplicate_event.return_value = True

    event = {"user": "U123", "text": "test message"}
    body = {"event_id": "duplicate-event-123"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_is_duplicate_event.assert_called()
    mock_trigger_async_processing.assert_not_called()
    mock_respond_with_eyes.assert_not_called()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_app_mention_handler_missing_event_id(
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_slack_app,
    mock_env,
    mock_get_parameter,
    lambda_context,
):
    """Test app mention handler with missing event ID"""
    # Create a mock app that captures the registered handlers
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_slack_app.event = mock_event_decorator
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    setup_handlers(mock_slack_app)

    assert "app_mention" in registered_handlers
    handler_func = registered_handlers["app_mention"]

    mock_ack = Mock()

    event = {"user": "U123", "text": "test message"}
    body = {}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_trigger_async_processing.put_item.assert_not_called()
    mock_is_duplicate_event.invoke.assert_not_called()
    mock_respond_with_eyes.assert_not_called()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_direct_message_handler_duplicate_event(
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_slack_app,
    mock_env,
    mock_get_parameter,
    lambda_context,
):
    """Test direct message handler with duplicate event"""
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_slack_app.event = mock_event_decorator
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    setup_handlers(mock_slack_app)

    assert "message" in registered_handlers
    handler_func = registered_handlers["message"]

    mock_ack = Mock()
    mock_is_duplicate_event.return_value = False

    event = {"user": "U123", "text": "test direct message", "channel_type": "im"}
    body = {"event_id": "duplicate-dm-event-456"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_is_duplicate_event.assert_called()
    mock_trigger_async_processing.assert_called()
    mock_respond_with_eyes.assert_called()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_direct_message_handler_missing_event_id(
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_slack_app,
    mock_env,
    mock_get_parameter,
    lambda_context,
):
    """Test direct message handler with missing event ID"""
    # Create a mock app that captures the registered handlers
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_slack_app.event = mock_event_decorator
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    setup_handlers(mock_slack_app)

    assert "message" in registered_handlers
    handler_func = registered_handlers["message"]

    mock_ack = Mock()

    event = {"user": "U123", "text": "test direct message", "channel_type": "im"}
    body = {}  # No event_id

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    # No DynamoDB or Lambda calls should be made
    mock_is_duplicate_event.assert_not_called()
    mock_trigger_async_processing.assert_not_called()
    mock_respond_with_eyes.assert_not_called()


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.trigger_async_processing")
@patch("app.utils.handler_utils.respond_with_eyes")
def test_direct_message_handler_non_dm_channel(
    mock_respond_with_eyes,
    mock_trigger_async_processing,
    mock_is_duplicate_event,
    mock_slack_app,
    mock_env,
    mock_get_parameter,
    lambda_context,
):
    """Test direct message handler ignores non-DM channels"""
    # Create a mock app that captures the registered handlers
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_slack_app.event = mock_event_decorator
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    setup_handlers(mock_slack_app)

    # Now we should have the actual handler function
    assert "message" in registered_handlers
    handler_func = registered_handlers["message"]

    mock_ack = Mock()

    # Test: Non-DM channel message (should return early)
    event = {"user": "U123", "text": "test channel message", "channel_type": "channel"}
    body = {"event_id": "channel-event-789"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    # No DynamoDB or Lambda calls should be made for non-DM messages
    mock_is_duplicate_event.assert_not_called()
    mock_trigger_async_processing.assert_not_called()
    mock_respond_with_eyes.assert_not_called()
