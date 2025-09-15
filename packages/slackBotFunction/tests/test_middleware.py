import sys
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError


def test_log_request_middleware_execution(mock_slack_app, mock_env, mock_get_parameter, lambda_context):
    """Test log_request middleware actual execution"""
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]

    from app.slack.slack_handlers import setup_handlers

    setup_handlers(mock_slack_app)

    # Verify the app.middleware decorator was called during import
    mock_slack_app.middleware.assert_called()

    # Get the middleware function that was registered
    middleware_calls = mock_slack_app.middleware.call_args_list
    assert len(middleware_calls) > 0

    # The middleware function should be the log_request function
    middleware_func = middleware_calls[0][0][0]  # First argument of first call

    # Now test calling the middleware function directly
    mock_next = Mock(return_value="middleware_result")
    mock_logger = Mock()
    test_body = {"test": "body"}

    # This should execute lines 56-57 in the log_request function
    result = middleware_func(mock_logger, test_body, mock_next)

    assert result == "middleware_result"
    mock_next.assert_called_once()


@patch("boto3.client")
def test_app_mention_handler_execution_simple(
    mock_boto_client, mock_slack_app, mock_env, mock_get_parameter, mock_table, lambda_context
):
    """Test app mention handler execution by simulating the handler registration process"""
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client
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

    # Test: Successful flow (no duplicate)
    event = {"user": "U123", "text": "test message"}
    body = {"event_id": "new-event-123"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_lambda_client.invoke.assert_called_once()
    mock_table.put_item.assert_called()


@patch("boto3.client")
def test_direct_message_handler_execution_simple(
    mock_boto_client, mock_slack_app, mock_env, mock_get_parameter, mock_table, lambda_context
):
    """Test direct message handler execution by simulating the handler registration process"""
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client
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

    # Test: Successful flow (no duplicate)
    event = {"user": "U123", "text": "test direct message", "channel_type": "im"}
    body = {"event_id": "new-event-456"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_lambda_client.invoke.assert_called_once()
    mock_table.put_item.assert_called()


@patch("boto3.client")
def test_app_mention_handler_duplicate_event(
    mock_boto_client, mock_slack_app, mock_env, mock_get_parameter, mock_table, lambda_context
):
    """Test app mention handler with duplicate event"""

    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client
    error = ClientError(error_response={"Error": {"Code": "ConditionalCheckFailedException"}}, operation_name="PutItem")
    mock_table.put_item.side_effect = error

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
    body = {"event_id": "duplicate-event-123"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_table.put_item.assert_called()
    mock_lambda_client.invoke.assert_not_called()


@patch("boto3.client")
def test_app_mention_handler_missing_event_id(
    mock_boto_client, mock_slack_app, mock_env, mock_get_parameter, mock_table, lambda_context
):
    """Test app mention handler with missing event ID"""
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client
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
    mock_table.put_item.assert_not_called()
    mock_lambda_client.invoke.assert_not_called()


@patch("boto3.client")
def test_direct_message_handler_duplicate_event(
    mock_boto_client, mock_slack_app, mock_env, mock_get_parameter, mock_table, lambda_context
):
    """Test direct message handler with duplicate event"""
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client
    error = ClientError(error_response={"Error": {"Code": "ConditionalCheckFailedException"}}, operation_name="PutItem")
    mock_table.put_item.side_effect = error

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
    body = {"event_id": "duplicate-dm-event-456"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_table.put_item.assert_called()
    mock_lambda_client.invoke.assert_not_called()


@patch("boto3.client")
def test_direct_message_handler_missing_event_id(
    mock_boto_client, mock_slack_app, mock_env, mock_get_parameter, mock_table, lambda_context
):
    """Test direct message handler with missing event ID"""
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client
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
    mock_table.put_item.assert_not_called()
    mock_lambda_client.invoke.assert_not_called()


@patch("boto3.client")
def test_direct_message_handler_non_dm_channel(
    mock_boto_client, mock_slack_app, mock_env, mock_get_parameter, mock_table, lambda_context
):
    """Test direct message handler ignores non-DM channels"""
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

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
    mock_table.put_item.assert_not_called()
    mock_lambda_client.invoke.assert_not_called()
