import sys


def test_app_mention_handler_registered(
    mock_slack_app,
    mock_env,
    mock_get_parameter,
    lambda_context,
):
    """Test app mention handler execution by simulating the handler registration process"""
    # set up mocks
    # Create a mock app that captures the registered handlers
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_slack_app.event = mock_event_decorator

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import setup_handlers

    # perform operation
    setup_handlers(mock_slack_app)

    # assertions
    assert "app_mention" in registered_handlers


def test_message_handler_registered(
    mock_slack_app,
    mock_env,
    mock_get_parameter,
    lambda_context,
):
    """Test direct message handler execution by simulating the handler registration process"""
    # set up mocks
    # Create a mock app that captures the registered handlers
    registered_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_handlers[event_type] = func
            return func

        return decorator

    mock_slack_app.event = mock_event_decorator

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import setup_handlers

    # perform operation
    setup_handlers(mock_slack_app)

    # assertions
    assert "message" in registered_handlers
