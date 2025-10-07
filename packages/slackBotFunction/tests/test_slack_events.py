import sys
from unittest import skip
from unittest.mock import Mock, patch


@patch("app.utils.handler_utils.forward_event_to_pull_request_lambda")
def test_process_async_slack_event_normal_message(
    mock_forward_event_to_pull_request_lambda: Mock,
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
    slack_event_data = {"text": "<@U123> test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"}
    with patch("app.slack.slack_events.process_feedback_event") as mock_process_feedback_event, patch(
        "app.slack.slack_events.process_slack_message"
    ) as mock_process_slack_message:
        process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)
        mock_forward_event_to_pull_request_lambda.assert_not_called()
        mock_process_feedback_event.assert_not_called()
        mock_process_slack_message.assert_called_once_with(
            event=slack_event_data, event_id="evt123", client=mock_client
        )


@patch("app.utils.handler_utils.forward_event_to_pull_request_lambda")
def test_process_async_slack_event_pull_request_with_mention(
    mock_forward_event_to_pull_request_lambda: Mock,
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
        "text": "<@U123> pr: 123 test question",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
    }
    with patch("app.slack.slack_events.process_feedback_event") as mock_process_feedback_event, patch(
        "app.slack.slack_events.process_slack_message"
    ) as mock_process_slack_message:
        process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)
        mock_forward_event_to_pull_request_lambda.assert_called_once_with(
            pull_request_id="123",
            event=slack_event_data,
            event_id="evt123",
            store_pull_request_id=True,
        )
        mock_process_feedback_event.assert_not_called()
        mock_process_slack_message.assert_not_called()


@patch("app.utils.handler_utils.forward_event_to_pull_request_lambda")
def test_process_async_slack_event_pull_request_with_no_mention(
    mock_forward_event_to_pull_request_lambda: Mock,
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
        "text": "pr: 123 test question",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
    }
    with patch("app.slack.slack_events.process_feedback_event") as mock_process_feedback_event, patch(
        "app.slack.slack_events.process_slack_message"
    ) as mock_process_slack_message:
        process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)
        mock_forward_event_to_pull_request_lambda.assert_called_once_with(
            pull_request_id="123",
            event=slack_event_data,
            event_id="evt123",
            store_pull_request_id=True,
        )
        mock_process_feedback_event.assert_not_called()
        mock_process_slack_message.assert_not_called()


@patch("app.utils.handler_utils.forward_event_to_pull_request_lambda")
def test_process_async_slack_event_feedback(
    mock_forward_event_to_pull_request_lambda: Mock,
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
        mock_forward_event_to_pull_request_lambda.assert_not_called()
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


def test_process_slack_message_empty_query(mock_get_parameter: Mock, mock_env: Mock):
    """Test async event processing with empty query"""
    # set up mocks
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {
        "text": "<@U123>",  # Only mention, no actual query
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
    }
    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    mock_client.chat_postMessage.assert_called_once_with(
        channel="C789",
        text="Hi there! Please ask me a question and I'll help you find information from our knowledge base.",
        thread_ts="1234567890.123",
    )


@patch("app.services.dynamo.get_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
@patch("app.slack.slack_events.get_conversation_session")
@patch("app.services.slack.post_error_message")
def test_process_slack_message_event_error(
    mock_post_error_message: Mock,
    mock_get_session: Mock,
    mock_reformulate_query: Mock,
    mock_query_bedrock: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test async event processing with error"""
    # set up mocks
    mock_query_bedrock.side_effect = Exception("Bedrock error")
    mock_reformulate_query.return_value = "test question"
    mock_get_session.return_value = None  # No existing session
    mock_client = Mock()

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {"text": "test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"}
    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    mock_post_error_message.assert_called_once_with(channel="C789", thread_ts="1234567890.123", client=mock_client)


@patch("app.services.dynamo.get_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
@patch("app.slack.slack_events.get_conversation_session")
@skip("skipped for demo purposes")
def test_process_slack_message_with_thread_ts(
    mock_get_session: Mock,
    mock_reformulate_query: Mock,
    mock_query_bedrock: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test async event processing with existing thread_ts"""
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}
    mock_query_bedrock.return_value = {"output": {"text": "AI response"}}
    mock_reformulate_query.return_value = "test question"
    mock_get_session.return_value = None  # No existing session

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
        from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {
        "text": "<@U123> test question",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
        "thread_ts": "1234567888.111",  # Existing thread
    }
    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    # Should be called at least once with the correct thread_ts
    assert mock_client.chat_postMessage.call_count >= 1
    first_call = mock_client.chat_postMessage.call_args_list[0]
    assert first_call[1]["thread_ts"] == "1234567888.111"
    assert first_call[1]["text"] == "AI response"


@patch("app.services.dynamo.get_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
@patch("app.slack.slack_events.get_conversation_session")
def test_regex_text_processing(
    mock_get_session: Mock,
    mock_reformulate_query: Mock,
    mock_query_bedrock: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # set up mocks
    mock_client = Mock()
    mock_query_bedrock.return_value = {"output": {"text": "AI response"}}
    mock_reformulate_query.return_value = "test question"
    mock_get_session.return_value = None  # No existing session

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {"text": "<@U123456> test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"}

    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    # Verify that the message was processed (query_bedrock was called)
    mock_query_bedrock.assert_called_once()
    # The actual regex processing happens inside the function
    assert mock_client.chat_postMessage.called


@patch("app.services.dynamo.get_state_information")
@patch("app.services.dynamo.store_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
def test_process_slack_message_with_session_storage(
    mock_reformulate_query: Mock,
    mock_query_bedrock: Mock,
    mock_store_state_information: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test async event processing that stores a new session"""
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}
    mock_query_bedrock.return_value = {
        "output": {"text": "AI response"},
        "sessionId": "new-session-123",
    }
    mock_reformulate_query.return_value = "test question"

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {"text": "test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"}

    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    # Verify session was stored - should be called twice (Q&A pair + session)
    assert mock_store_state_information.call_count >= 1


@patch("app.services.dynamo.get_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
@patch("app.slack.slack_events.get_conversation_session")
def test_process_slack_message_chat_update_error(
    mock_get_session: Mock,
    mock_reformulate_query: Mock,
    mock_query_bedrock: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test process_async_slack_event with chat_update error"""
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.side_effect = Exception("Update failed")
    mock_query_bedrock.return_value = {"output": {"text": "AI response"}}
    mock_reformulate_query.return_value = "test question"
    mock_get_session.return_value = None  # No existing session

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {"text": "<@U123> test question", "user": "U456", "channel": "C789", "ts": "1234567890.123"}
    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    # no assertions as we are just checking it does not throw an error


@patch("app.services.dynamo.get_state_information")
@patch("app.services.bedrock.query_bedrock")
@patch("app.services.query_reformulator.reformulate_query")
@patch("app.slack.slack_events.get_conversation_session")
def test_process_slack_message_dm_context(
    mock_get_session: Mock,
    mock_reformulate_query: Mock,
    mock_query_bedrock: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test process_async_slack_event with DM context"""
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "123"}
    mock_query_bedrock.return_value = {"output": {"text": "AI response"}, "sessionId": "new-session"}
    mock_get_session.return_value = None

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_event

    # perform operation
    slack_event_data = {
        "text": "test question",
        "user": "U456",
        "channel": "D789",
        "ts": "123",
        "channel_type": "im",  # DM context
    }
    process_async_slack_event(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    # no assertions as we are just checking it does not throw an error


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
            text='Please let us know how the answer could be improved. Start your message with "feedback:"',
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
