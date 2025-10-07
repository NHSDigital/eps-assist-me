import sys
from unittest.mock import ANY, Mock, patch


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.extract_pull_request_id")
def test_process_pull_request_event(
    mock_extract_pull_request_id: Mock, mock_is_duplicate_event: Mock, mock_env: Mock, mock_get_parameter: Mock
):
    # set up mocks
    mock_is_duplicate_event.return_value = False
    mock_extract_pull_request_id.return_value = None, "test question"

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_pull_request_slack_event

    # perform operation
    # patching process_async_slack_event here as its in the same module we are testing
    with patch("app.slack.slack_events.process_async_slack_event") as mock_process_async_slack_event:
        slack_event_data = {
            "event": {
                "text": "test question",
                "user": "U456",
                "channel": "C789",
                "ts": "1234567890.123",
                "thread_ts": "1234567888.111",  # Existing thread
            },
            "event_id": "evt123",
        }
        process_pull_request_slack_event(slack_event_data)

        # assertions
        expected_slack_event_data = {
            "text": "test question",
            "user": "U456",
            "channel": "C789",
            "ts": "1234567890.123",
            "thread_ts": "1234567888.111",  # Existing thread
        }
        mock_process_async_slack_event.assert_called_once_with(
            event=expected_slack_event_data, event_id="evt123", client=ANY
        )


@patch("app.utils.handler_utils.is_duplicate_event")
@patch("app.utils.handler_utils.extract_pull_request_id")
def test_process_pull_request_duplicate_event(
    mock_extract_pull_request_id: Mock, mock_is_duplicate_event: Mock, mock_env: Mock
):
    # set up mocks
    mock_is_duplicate_event.return_value = True

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_pull_request_slack_event

    # perform operation
    slack_event_data = {
        "event": {
            "text": "pr: 60 test question",
            "user": "U456",
            "channel": "C789",
            "ts": "1234567890.123",
            "thread_ts": "1234567888.111",  # Existing thread
        },
        "event_id": "evt123",
    }
    process_pull_request_slack_event(slack_event_data)

    # assertions
    mock_extract_pull_request_id.assert_not_called()
