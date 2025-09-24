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
    registered_ack_handlers = {}

    def mock_event_decorator(event_type):
        def decorator(ack, lazy):
            func = lazy[0]
            registered_event_handlers[event_type] = func
            registered_ack_handlers[event_type] = ack
            return func

        return decorator

    def mock_action_decorator(event_type):
        def decorator(ack, lazy):
            func = lazy[0]
            registered_action_handlers[event_type] = func
            registered_ack_handlers[event_type] = ack
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

    assert registered_ack_handlers["app_mention"].__name__ == "respond_to_events"
    assert registered_ack_handlers["message"].__name__ == "respond_to_events"
    assert registered_ack_handlers["feedback_yes"].__name__ == "respond_to_action"
    assert registered_ack_handlers["feedback_no"].__name__ == "respond_to_action"

    assert registered_event_handlers["app_mention"].__name__ == "mention_handler"
    assert registered_event_handlers["message"].__name__ == "unified_message_handler"
    assert registered_action_handlers["feedback_yes"].__name__ == "feedback_handler"
    assert registered_action_handlers["feedback_no"].__name__ == "feedback_handler"
