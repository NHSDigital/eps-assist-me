import sys
from unittest.mock import Mock


def test_correct_handlers_registered(
    mock_slack_app: Mock,
    mock_env: Mock,
    mock_get_parameter: Mock,
    lambda_context: Mock,
):
    """Test app mention handler execution by simulating the handler registration process"""
    # set up mocks
    # Create a mock app that captures the registered handlers
    registered_action_handlers = {}
    registered_event_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(func):
            registered_event_handlers[event_type] = func
            return func

        return decorator

    def mock_action_decorator(event_type):
        def decorator(func):
            registered_action_handlers[event_type] = func
            return func

        return decorator

    mock_slack_app.event = mock_event_decorator
    mock_slack_app.action = mock_action_decorator

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import setup_handlers

    # perform operation
    setup_handlers(mock_slack_app)

    # assertions
    assert "app_mention" in registered_event_handlers
    assert "message" in registered_event_handlers
    assert "feedback_yes" in registered_action_handlers
    assert "feedback_no" in registered_action_handlers
