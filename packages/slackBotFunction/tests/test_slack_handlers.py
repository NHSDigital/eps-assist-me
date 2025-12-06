import sys
from unittest.mock import Mock, patch


# unified message handler
@patch("app.slack.slack_events.process_async_slack_event")
@patch("app.utils.handler_utils.extract_session_pull_request_id")
@patch("app.utils.handler_utils.forward_event_to_pull_request_lambda")
@patch("app.utils.handler_utils.gate_common")
def test_unified_message_handler_successful_call(
    mock_gate_common: Mock,
    mock_forward_event_to_pull_request_lambda: Mock,
    mock_extract_session_pull_request_id: Mock,
    mock_process_async_slack_event: Mock,
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
    mock_extract_session_pull_request_id.return_value = None
    mock_gate_common.return_value = "evt123"

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import unified_message_handler

    # perform operation
    unified_message_handler(event=mock_event, body=mock_body, client=mock_client)

    # assertions
    mock_process_async_slack_event.assert_called_once_with(event=mock_event, event_id="evt123", client=mock_client)
    mock_forward_event_to_pull_request_lambda.assert_not_called()


@patch("app.slack.slack_events.process_async_slack_event")
@patch("app.utils.handler_utils.extract_session_pull_request_id")
@patch("app.utils.handler_utils.forward_event_to_pull_request_lambda")
@patch("app.utils.handler_utils.gate_common")
def test_unified_message_handler_messages_with_no_thread_are_dropped(
    mock_gate_common: Mock,
    mock_forward_event_to_pull_request_lambda: Mock,
    mock_extract_session_pull_request_id: Mock,
    mock_process_async_slack_event: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test app mention handler execution"""
    # set up mocks
    mock_event = {
        "user": "U123",
        "text": "<@U456> test",
        "channel": "C123",
        "channel_type": "group",
        "type": "message",
    }
    mock_body = {"event_id": "evt123"}
    mock_client = Mock()
    mock_extract_session_pull_request_id.return_value = None
    mock_gate_common.return_value = "evt123"

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import unified_message_handler

    # perform operation
    unified_message_handler(event=mock_event, body=mock_body, client=mock_client)

    # assertions
    mock_process_async_slack_event.assert_not_called()
    mock_forward_event_to_pull_request_lambda.assert_not_called()


@patch("app.slack.slack_events.process_async_slack_event")
@patch("app.utils.handler_utils.extract_session_pull_request_id")
@patch("app.utils.handler_utils.forward_event_to_pull_request_lambda")
@patch("app.utils.handler_utils.gate_common")
def test_unified_message_handler_pull_request_call(
    mock_gate_common: Mock,
    mock_forward_event_to_pull_request_lambda: Mock,
    mock_extract_session_pull_request_id: Mock,
    mock_process_async_slack_event: Mock,
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
    mock_extract_session_pull_request_id.return_value = "123"
    mock_gate_common.return_value = "evt123"

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import unified_message_handler

    # perform operation
    unified_message_handler(event=mock_event, body=mock_body, client=mock_client)

    # assertions
    mock_forward_event_to_pull_request_lambda.assert_called_once_with(
        event=mock_event, pull_request_id="123", event_id="evt123", store_pull_request_id=False
    )
    mock_process_async_slack_event.assert_not_called()


# feedback action handler
@patch("app.slack.slack_events.process_async_slack_action")
@patch("app.utils.handler_utils.extract_session_pull_request_id")
@patch("app.utils.handler_utils.forward_action_to_pull_request_lambda")
def test_feedback_handler_success(
    mock_forward_action_to_pull_request_lambda: Mock,
    mock_extract_session_pull_request_id: Mock,
    mock_process_async_slack_action: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback_yes action handler"""
    # setup mocks
    mock_extract_session_pull_request_id.return_value = None

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
    mock_process_async_slack_action.assert_called_once_with(
        body=mock_body,
        client=mock_client,
    )
    mock_forward_action_to_pull_request_lambda.assert_not_called()


@patch("app.slack.slack_events.process_async_slack_action")
@patch("app.utils.handler_utils.extract_session_pull_request_id")
@patch("app.utils.handler_utils.forward_action_to_pull_request_lambda")
def test_feedback_handler_pull_request(
    mock_forward_action_to_pull_request_lambda: Mock,
    mock_extract_session_pull_request_id: Mock,
    mock_process_async_slack_action: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test feedback_yes action handler"""
    # setup mocks
    mock_extract_session_pull_request_id.return_value = "123"

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
    mock_forward_action_to_pull_request_lambda.assert_called_once_with(
        body=mock_body,
        pull_request_id="123",
    )
    mock_process_async_slack_action.assert_not_called()


@patch("app.slack.slack_events.open_citation")
@patch("app.utils.handler_utils.extract_session_pull_request_id")
@patch("app.utils.handler_utils.forward_action_to_pull_request_lambda")
def test_citation(
    mock_forward_action_to_pull_request_lambda: Mock,
    mock_extract_session_pull_request_id: Mock,
    mock_open_citation: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test citations action handler"""
    # setup mocks
    mock_extract_session_pull_request_id.return_value = None

    mock_body = {
        "user": {"id": "U123"},
        "actions": [
            {
                "action_id": "cite",
                "value": '{"ck": "conv-key", "ch": "C123", "tt": "123", "mt": "456", "title": "title", "body": "body",'
                + '"link": "citation_link"}',
            }
        ],
        "channel": {"id": "C123"},
        "message": {"ts": "123", "blocks": []},
    }
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_handlers" in sys.modules:
        del sys.modules["app.slack.slack_handlers"]
    from app.slack.slack_handlers import feedback_handler

    # perform operation
    feedback_handler(body=mock_body, client=mock_client)

    # assertions
    mock_open_citation.assert_called_once()
    mock_forward_action_to_pull_request_lambda.assert_not_called()
