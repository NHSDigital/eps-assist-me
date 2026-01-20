import sys
import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def mock_logger():
    return MagicMock()


@patch("app.utils.handler_utils.forward_to_pull_request_lambda")
def test_process_async_slack_event_feedback(
    mock_forward_to_pull_request_lambda: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test successful async event processing"""
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_event

    # perform operation
    slack_event_data = {
        "text": "feedback: this is some feedback",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
    }
    with patch("app.slack.slack_events.process_feedback_event") as mock_process_feedback_event, patch(
        "app.slack.slack_events.process_slack_message"
    ) as mock_process_slack_message:
        process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)
        mock_forward_to_pull_request_lambda.assert_not_called()
        mock_process_feedback_event.assert_called_once_with(
            message_text="feedback: this is some feedback",
            conversation_key="thread#C789#1234567890.123",
            user_id="U456",
            channel_id="C789",
            thread_root="1234567890.123",
            client=mock_client,
            event=slack_event_data,
        )
        mock_process_slack_message.assert_not_called()


@patch("app.utils.handler_utils.is_latest_message")
def test_process_async_slack_action_positive(
    mock_is_latest_message: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test successful async action processing"""
    # set up mocks
    mock_client = Mock()
    mock_is_latest_message.return_value = True

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_action

    feedback_value = '{"ck":"thread#C123#123","ch":"C123","mt":"1759845126.972219","tt":"1759845114.407989"}'

    # perform operation
    slack_action_data = {
        "type": "block_actions",
        "user": {"id": "U123"},
        "channel": {"id": "C123"},
        "message": {"ts": "1759845126.972219"},
        "actions": [{"action_id": "feedback_yes", "value": feedback_value}],
    }
    with patch("app.slack.slack_events.store_feedback") as mock_store_feedback:
        process_async_slack_action(body=slack_action_data, client=mock_client)

        # assertions
        mock_store_feedback.assert_called_once_with(
            conversation_key="thread#C123#123",
            feedback_type="positive",
            user_id="U123",
            channel_id="C123",
            thread_ts="1759845114.407989",
            message_ts="1759845126.972219",
            client=mock_client,
        )
        mock_client.chat_postMessage.assert_called_once_with(
            channel="C123",
            text="Thank you for your feedback.",
            thread_ts="1759845114.407989",
        )


@patch("app.utils.handler_utils.is_latest_message")
def test_process_async_slack_action_negative(
    mock_is_latest_message: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test successful async action processing"""
    # set up mocks
    mock_client = Mock()
    mock_is_latest_message.return_value = True

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_action

    feedback_value = '{"ck":"thread#C123#123","ch":"C123","mt":"1759845126.972219","tt":"1759845114.407989"}'

    # perform operation
    slack_action_data = {
        "type": "block_actions",
        "user": {"id": "U123"},
        "channel": {"id": "C123"},
        "message": {"ts": "1759845126.972219"},
        "actions": [{"action_id": "feedback_no", "value": feedback_value}],
    }
    with patch("app.slack.slack_events.store_feedback") as mock_store_feedback:
        process_async_slack_action(body=slack_action_data, client=mock_client)

        # assertions
        mock_store_feedback.assert_called_once_with(
            conversation_key="thread#C123#123",
            feedback_type="negative",
            user_id="U123",
            channel_id="C123",
            thread_ts="1759845114.407989",
            message_ts="1759845126.972219",
            client=mock_client,
        )
        mock_client.chat_postMessage.assert_called_once_with(
            channel="C123",
            text=(
                "Please let us know how the answer could be improved. Do not enter any personal data.\n"
                + 'Start your message with "feedback:"'
            ),
            thread_ts="1759845114.407989",
        )


@patch("app.utils.handler_utils.is_latest_message")
def test_process_async_slack_action_not_latest(
    mock_is_latest_message: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test successful async action processing"""
    # set up mocks
    mock_client = Mock()
    mock_is_latest_message.return_value = False

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_action

    feedback_value = '{"ck":"thread#C123#123","ch":"C123","mt":"1759845126.972219","tt":"1759845114.407989"}'

    # perform operation
    slack_action_data = {
        "type": "block_actions",
        "user": {"id": "U123"},
        "channel": {"id": "C123"},
        "actions": [{"action_id": "feedback_no", "value": feedback_value}],
    }
    with patch("app.slack.slack_events.store_feedback") as mock_store_feedback:
        process_async_slack_action(body=slack_action_data, client=mock_client)

        # assertions
        mock_store_feedback.assert_not_called()
        mock_client.chat_postMessage.assert_not_called()


@patch("app.utils.handler_utils.is_latest_message")
def test_process_async_slack_action_unknown_action(
    mock_is_latest_message: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test successful async action processing"""
    # set up mocks
    mock_client = Mock()
    mock_is_latest_message.return_value = True

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_action

    feedback_value = '{"ck":"thread#C123#123","ch":"C123","mt":"1759845126.972219","tt":"1759845114.407989"}'

    # perform operation
    slack_action_data = {
        "type": "block_actions",
        "user": {"id": "U123"},
        "channel": {"id": "C123"},
        "actions": [{"action_id": "I_Do_Not_Know_This_Action", "value": feedback_value}],
    }
    with patch("app.slack.slack_events.store_feedback") as mock_store_feedback:
        process_async_slack_action(body=slack_action_data, client=mock_client)

        # assertions
        mock_store_feedback.assert_not_called()
        mock_client.chat_postMessage.assert_not_called()


def test_process_feedback_event():
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_feedback_event

    # perform operation
    mock_event = {}
    with patch("app.slack.slack_events.store_feedback") as mock_store_feedback:
        process_feedback_event(
            message_text="feedback: this is some feedback",
            conversation_key="thread#C123#123",
            user_id="U123",
            channel_id="C123",
            thread_root="1759845114.407989",
            event=mock_event,
            client=mock_client,
        )

        # assertions
        mock_store_feedback.assert_called_once_with(
            conversation_key="thread#C123#123",
            feedback_type="additional",
            user_id="U123",
            channel_id="C123",
            thread_ts="1759845114.407989",
            message_ts=None,
            feedback_text="this is some feedback",
            client=mock_client,
        )
        mock_client.chat_postMessage.assert_called_once_with(
            channel="C123", text="Thank you for your feedback.", thread_ts="1759845114.407989"
        )


@patch("app.services.slack.post_error_message")
def test_process_feedback_event_error(
    mock_post_error_message: Mock,
):
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_feedback_event

    # perform operation
    mock_event = {
        "channel": "C123",
        "thread_ts": "123",
    }
    with patch("app.slack.slack_events.store_feedback") as mock_store_feedback:
        mock_store_feedback.side_effect = Exception("There was an error")
        process_feedback_event(
            message_text="feedback: this is some feedback",
            conversation_key="thread#C123#123",
            user_id="U123",
            channel_id="C123",
            thread_root="1759845114.407989",
            event=mock_event,
            client=mock_client,
        )

        # assertions
        mock_post_error_message.assert_called_once_with(channel="C123", thread_ts="123", client=mock_client)
