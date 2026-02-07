from unittest.mock import Mock, patch
from app.services.slack import get_friendly_channel_name
from app.slack.slack_events import process_slack_message, log_query_stats
import sys

# Remove modules from cache to ensure fresh import with mocks if needed
for module in list(sys.modules.keys()):
    if module.startswith("app"):
        del sys.modules[module]


def test_get_friendly_channel_name_returns_direct_message_for_im():
    mock_client = Mock()
    mock_client.conversations_info.return_value = {"ok": True, "channel": {"is_im": True, "id": "D12345"}}

    result = get_friendly_channel_name("D12345", mock_client)
    assert result == "Direct Message"


def test_get_friendly_channel_name_returns_name_for_public_channel():
    mock_client = Mock()
    mock_client.conversations_info.return_value = {
        "ok": True,
        "channel": {"is_im": False, "name": "general", "id": "C12345"},
    }

    result = get_friendly_channel_name("C12345", mock_client)
    assert result == "general"


@patch("app.slack.slack_events.logger")
def test_log_query_stats_masks_dm_channel(mock_logger, mock_env, mock_get_parameter):
    mock_client = Mock()
    # verify we don't call client.conversations_info because we handle it explicitly

    event = {"event_ts": "1234567890.123", "channel_type": "im"}

    log_query_stats(user_query="test", event=event, channel="D123", client=mock_client, thread_ts="123")

    # Check if info was called
    assert mock_logger.info.called

    # Inspect arguments
    args, kwargs = mock_logger.info.call_args
    reporting_info = kwargs["extra"]["reporting_info"]
    assert reporting_info["channel"] == "Direct Message"
    assert reporting_info["is_direct_message"] is True
    # Ensure no API call was made to fetch channel name (optimization check)
    mock_client.conversations_info.assert_not_called()


@patch("app.slack.slack_events.logger")
@patch("app.slack.slack_events.conversation_key_and_root")
@patch("app.slack.slack_events.get_conversation_session_data")
@patch("app.slack.slack_events.get_friendly_channel_name")
@patch("app.services.ai_processor.process_ai_query")
def test_process_slack_message_log_privacy(
    mock_process_ai, mock_get_friendly, mock_get_session, mock_key_root, mock_logger, mock_env, mock_get_parameter
):
    mock_key_root.return_value = ("key", "ts")
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "123"}
    mock_get_session.return_value = {}
    mock_process_ai.return_value = {"kb_response": {}, "text": "response", "session_id": "sid"}

    event = {
        "user": "U12345",
        "channel": "C123",
        "text": "hello",
        "ts": "123",
        "event_ts": "123",
        "channel_type": "channel",
    }

    process_slack_message(event, "evt1", mock_client)

    # Verify the "Processing message" log call
    # It should NOT contain the user ID "U12345" in the message string

    # Find the call with "Processing message"
    processing_call = None
    for call in mock_logger.info.call_args_list:
        args, _ = call
        if args and "Processing message" in args[0]:
            processing_call = call
            break

    assert processing_call is not None
    # The message should be exactly "Processing message" (or at least not contain "from user U12345")
    # call args is a tuple (args, kwargs)
    args, _ = processing_call
    assert "from user" not in args[0]
    assert "U12345" not in args[0]
