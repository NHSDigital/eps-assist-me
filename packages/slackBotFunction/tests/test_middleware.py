import json
import sys
from unittest.mock import Mock, patch


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_log_request(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test middleware function behavior"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app" in sys.modules:
        del sys.modules["app"]

    # Test that the middleware function exists and can be imported
    from app.util.slack_handlers import setup_handlers

    assert callable(setup_handlers)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_log_request_middleware_execution_fixed(mock_boto_resource, mock_get_parameter, mock_app_class, mock_env):
    """Test log_request middleware actual execution to cover lines 56-57"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock the app instance and middleware registration
    mock_app_instance = Mock()
    mock_app_class.return_value = mock_app_instance

    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    if "app.util.slack_handlers" in sys.modules:
        del sys.modules["app.util.slack_handlers"]

    # Import the module to register the middleware
    import app.main  # noqa: F401

    # Verify the app.middleware decorator was called during import
    mock_app_instance.middleware.assert_called()

    # Get the middleware function that was registered
    middleware_calls = mock_app_instance.middleware.call_args_list
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


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
@patch("time.time")
def test_app_mention_handler_execution_simple(
    mock_time, mock_boto_client, mock_boto_resource, mock_get_parameter, mock_app_class, mock_env
):
    """Test app mention handler execution by simulating the handler registration process"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_time.return_value = 1000

    mock_table = Mock()
    mock_table.put_item.return_value = None  # successful put_item by default
    mock_boto_resource.return_value.Table.return_value = mock_table

    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    # Create a mock app that captures the registered handlers
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_app_instance = Mock()
    mock_app_instance.event = mock_event_decorator
    mock_app_class.return_value = mock_app_instance

    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    if "app.util.slack_handlers" in sys.modules:
        del sys.modules["app.util.slack_handlers"]

    # Import the module to register the handlers
    import app.main  # noqa: F401

    # Now we should have the actual handler function
    assert "app_mention" in registered_handlers
    handler_func = registered_handlers["app_mention"]

    mock_ack = Mock()

    # Test: Successful flow (no duplicate)
    event = {"user": "U123", "text": "test message"}
    body = {"event_id": "new-event-123"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_table.put_item.assert_called()
    mock_lambda_client.invoke.assert_called()


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
@patch("time.time")
def test_direct_message_handler_execution_simple(
    mock_time, mock_boto_client, mock_boto_resource, mock_get_parameter, mock_app_class, mock_env
):
    """Test direct message handler execution by simulating the handler registration process"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_time.return_value = 1000

    mock_table = Mock()
    mock_table.put_item.return_value = None  # successful put_item by default
    mock_boto_resource.return_value.Table.return_value = mock_table

    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    # Create a mock app that captures the registered handlers
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_app_instance = Mock()
    mock_app_instance.event = mock_event_decorator
    mock_app_class.return_value = mock_app_instance

    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    if "app.util.slack_handlers" in sys.modules:
        del sys.modules["app.util.slack_handlers"]

    # Import the module to register the handlers
    import app.main  # noqa: F401

    # Now we should have the actual handler function
    assert "message" in registered_handlers
    handler_func = registered_handlers["message"]

    mock_ack = Mock()

    # Test: Successful flow (no duplicate)
    event = {"user": "U123", "text": "test direct message", "channel_type": "im"}
    body = {"event_id": "new-event-456"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_table.put_item.assert_called()
    mock_lambda_client.invoke.assert_called()


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
@patch("time.time")
def test_app_mention_handler_duplicate_event(
    mock_time, mock_boto_client, mock_boto_resource, mock_get_parameter, mock_app_class, mock_env
):
    """Test app mention handler with duplicate event"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_time.return_value = 1000

    mock_table = Mock()
    from botocore.exceptions import ClientError

    error = ClientError(error_response={"Error": {"Code": "ConditionalCheckFailedException"}}, operation_name="PutItem")
    mock_table.put_item.side_effect = error
    mock_boto_resource.return_value.Table.return_value = mock_table

    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_app_instance = Mock()
    mock_app_instance.event = mock_event_decorator
    mock_app_class.return_value = mock_app_instance

    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    if "app.util.slack_handlers" in sys.modules:
        del sys.modules["app.util.slack_handlers"]

    import app.main  # noqa: F401

    assert "app_mention" in registered_handlers
    handler_func = registered_handlers["app_mention"]

    mock_ack = Mock()

    event = {"user": "U123", "text": "test message"}
    body = {"event_id": "duplicate-event-123"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_table.put_item.assert_called()
    mock_lambda_client.invoke.assert_not_called()


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
@patch("time.time")
def test_app_mention_handler_missing_event_id(
    mock_time, mock_boto_client, mock_boto_resource, mock_get_parameter, mock_app_class, mock_env
):
    """Test app mention handler with missing event ID"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_time.return_value = 1000

    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table

    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_app_instance = Mock()
    mock_app_instance.event = mock_event_decorator
    mock_app_class.return_value = mock_app_instance

    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    if "app.util.slack_handlers" in sys.modules:
        del sys.modules["app.util.slack_handlers"]

    import app.main  # noqa: F401

    assert "app_mention" in registered_handlers
    handler_func = registered_handlers["app_mention"]

    mock_ack = Mock()

    event = {"user": "U123", "text": "test message"}
    body = {}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_table.put_item.assert_not_called()
    mock_lambda_client.invoke.assert_not_called()


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
@patch("time.time")
def test_direct_message_handler_duplicate_event(
    mock_time, mock_boto_client, mock_boto_resource, mock_get_parameter, mock_app_class, mock_env
):
    """Test direct message handler with duplicate event"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_time.return_value = 1000

    mock_table = Mock()
    from botocore.exceptions import ClientError

    error = ClientError(error_response={"Error": {"Code": "ConditionalCheckFailedException"}}, operation_name="PutItem")
    mock_table.put_item.side_effect = error
    mock_boto_resource.return_value.Table.return_value = mock_table

    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_app_instance = Mock()
    mock_app_instance.event = mock_event_decorator
    mock_app_class.return_value = mock_app_instance

    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    if "app.util.slack_handlers" in sys.modules:
        del sys.modules["app.util.slack_handlers"]

    import app.main  # noqa: F401

    assert "message" in registered_handlers
    handler_func = registered_handlers["message"]

    mock_ack = Mock()

    event = {"user": "U123", "text": "test direct message", "channel_type": "im"}
    body = {"event_id": "duplicate-dm-event-456"}

    handler_func(event, mock_ack, body)

    mock_ack.assert_called()
    mock_table.put_item.assert_called()
    mock_lambda_client.invoke.assert_not_called()


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
@patch("time.time")
def test_direct_message_handler_missing_event_id(
    mock_time, mock_boto_client, mock_boto_resource, mock_get_parameter, mock_app_class, mock_env
):
    """Test direct message handler with missing event ID"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_time.return_value = 1000

    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table

    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_app_instance = Mock()
    mock_app_instance.event = mock_event_decorator
    mock_app_class.return_value = mock_app_instance

    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    if "app.util.slack_handlers" in sys.modules:
        del sys.modules["app.util.slack_handlers"]

    import app.main  # noqa: F401

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


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
@patch("time.time")
def test_direct_message_handler_non_dm_channel(
    mock_time, mock_boto_client, mock_boto_resource, mock_get_parameter, mock_app_class, mock_env
):
    """Test direct message handler ignores non-DM channels"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_time.return_value = 1000

    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table

    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    # Create a mock app that captures the registered handlers
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_app_instance = Mock()
    mock_app_instance.event = mock_event_decorator
    mock_app_class.return_value = mock_app_instance

    if "app.main" in sys.modules:
        del sys.modules["app.main"]
    if "app.core.config" in sys.modules:
        del sys.modules["app.core.config"]
    if "app.util.slack_handlers" in sys.modules:
        del sys.modules["app.util.slack_handlers"]

    # Import the module to register the handlers
    import app.main  # noqa: F401

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
