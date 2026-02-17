import sys
from unittest.mock import Mock, patch
from app.services.slack import get_friendly_channel_name


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


def test_log_query_stats_masks_dm_channel(mock_env, mock_get_parameter):
    # reload module to ensure clean state and correct patching
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    from app.slack.slack_events import log_query_stats
    import app.slack.slack_events

    mock_client = Mock()

    event = {"event_ts": "1234567890.123", "channel_type": "im"}

    with patch.object(app.slack.slack_events, "logger") as mock_logger:
        log_query_stats(user_query="test", event=event, channel="D123", client=mock_client, thread_ts="123")

        assert mock_logger.info.called

        args, kwargs = mock_logger.info.call_args
        reporting_info = kwargs["extra"]["reporting_info"]
        assert reporting_info["channel"] == "Direct Message"
        assert reporting_info["is_direct_message"] is True

        mock_client.conversations_info.assert_not_called()


def test_process_slack_message_log_privacy(mock_env, mock_get_parameter):
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    from app.slack.slack_events import process_slack_message
    import app.slack.slack_events

    with patch.object(app.slack.slack_events, "logger") as mock_logger, patch.object(
        app.slack.slack_events, "conversation_key_and_root", return_value=("key", "ts")
    ), patch.object(app.slack.slack_events, "get_conversation_session_data", return_value={}), patch.object(
        app.slack.slack_events, "get_friendly_channel_name"
    ), patch.object(
        app.slack.slack_events, "process_ai_query"
    ) as mock_process_ai:

        mock_client = Mock()
        mock_client.chat_postMessage.return_value = {"ts": "123"}
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

        processing_call = None
        for call in mock_logger.info.call_args_list:
            args, _ = call
            if args and "Processing message" in args[0]:
                processing_call = call
                break

        assert processing_call is not None
        args, _ = processing_call
        assert "from user" not in args[0]
        assert "U12345" not in args[0]
