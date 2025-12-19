import json
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch


@pytest.fixture
def mock_logger():
    return MagicMock()


@patch("app.services.dynamo.get_state_information")
@patch("app.services.ai_processor.process_ai_query")
@patch("app.slack.slack_events.get_conversation_session")
@patch("app.slack.slack_events._create_feedback_blocks")
def test_citation_processing(
    mock_get_session: Mock,
    mock_process_ai_query: Mock,
    mock_create_feedback_blocks: Mock,
    mock_get_state_information: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test block builder is being called correctly"""
    # set up mocks
    mock_client = Mock()
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "session-123",
        "citations": [],
        "kb_response": {"output": {"text": "AI response"}},
    }
    mock_get_session.return_value = None  # No existing session

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_slack_message

    # perform operation
    slack_event_data = {
        "text": "Answer",
        "user": "U456",
        "channel": "C789",
        "ts": "1234567890.123",
    }

    process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

    # assertions
    # Verify that the message was processed (process_ai_query was called)
    mock_create_feedback_blocks.assert_called_once()


def test_process_slack_message_split_citation():
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}


def test_process_citation_events_update_chat():
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import process_async_slack_action

    body = {
        "type": "block_actions",
        "message": {
            "ts": "123",
            "text": "",
            "blocks": [
                {
                    "type": "section",
                    "block_id": "OvNCm",
                    "text": {
                        "type": "mrkdwn",
                        "text": "",
                    },
                },
                {
                    "type": "actions",
                    "block_id": "citation_actions",
                    "elements": [
                        {
                            "type": "button",
                            "action_id": "cite_1",
                            "text": {
                                "type": "plain_text",
                                "text": "[1] Downloading a single prescription using the prescription's ID, or ...",
                                "emoji": "true",
                            },
                            "value": '{"ck":"123","ch":"123","mt":"123","tt":"123","source_number":"1","title":"title"',
                        }
                    ],
                },
            ],
        },
        "channel": {
            "id": "ABC123",
        },
        "actions": [
            {
                "action_id": "cite_1",
                "block_id": "citation_actions",
                "text": {
                    "type": "plain_text",
                    "text": "[1] Downloading a single prescription using the prescription's ID, or ...",
                    "emoji": "true",
                },
                "value": '{"ck":"123","ch":"C095D4SRX6W","mt":"123","tt":"123","source_number":"1","title":""}',
                "type": "button",
                "action_ts": "1765807735.805872",
            }
        ],
    }

    # perform operation
    process_async_slack_action(body, mock_client)

    # assertions
    mock_client.chat_update.assert_called()


def test_process_citation_events_update_chat_message_open_citation():
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import open_citation

    params = {
        "ck": "123123",
        "ch": "123123",
        "mt": "123123.123123",
        "tt": "123123.123123",
        "source_number": "1",
        "title": "Citation Title",
        "body": "Citation Body",
        "relevance_score": "0.95",
    }

    citations = {
        "type": "actions",
        "block_id": "citation_actions",
        "elements": [
            {
                "type": "button",
                "action_id": "cite_1",
                "text": {
                    "type": "plain_text",
                    "text": "[1] The body of the citation",
                    "emoji": "true",
                },
                "style": None,  # Set citation as de-active
                "value": str(params),
            },
        ],
    }

    message = {
        "blocks": [citations],
    }

    # perform operation
    open_citation("ABC", "123", message, params, mock_client)

    # assertions
    expected_blocks = [
        citations,
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Citation Title*\n\n> Citation Body"},
            "block_id": "citation_block",
        },
    ]
    mock_client.chat_update.assert_called()
    mock_client.chat_update.assert_called_with(channel="ABC", ts="123", blocks=expected_blocks)


def test_process_citation_events_update_chat_message_close_citation():
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import open_citation

    params = {
        "ck": "123123",
        "ch": "123123",
        "mt": "123123.123123",
        "tt": "123123.123123",
        "source_number": "1",
        "title": "Citation Title",
        "body": "Citation Body",
        "relevance_score": "0.95",
    }

    citations = {
        "type": "actions",
        "block_id": "citation_actions",
        "elements": [
            {
                "type": "button",
                "action_id": "cite_1",
                "text": {
                    "type": "plain_text",
                    "text": "[1] The body of the citation",
                    "emoji": "true",
                },
                "style": "primary",  # Set citation as active
                "value": str(params),
            },
        ],
    }

    citation_body = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*Citation Title*\n\n> Citation Body"},
        "block_id": "citation_block",
    }

    message = {
        "blocks": [citations, citation_body],
    }

    # perform operation
    open_citation("ABC", "123", message, params, mock_client)

    # assertions
    expected_blocks = [
        citations,
    ]
    mock_client.chat_update.assert_called()
    mock_client.chat_update.assert_called_with(channel="ABC", ts="123", blocks=expected_blocks)


def test_process_citation_events_update_chat_message_change_close_citation():
    # set up mocks
    mock_client = Mock()
    mock_client.chat_postMessage.return_value = {"ts": "1234567890.124"}
    mock_client.chat_update.return_value = {"ok": True}

    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import open_citation

    params = {
        "ck": "123123",
        "ch": "123123",
        "mt": "123123.123123",
        "tt": "123123.123123",
        "source_number": "2",
        "title": "Second Citation Title",
        "body": "Second Citation Body",
        "relevance_score": "0.95",
    }

    citations = {
        "type": "actions",
        "block_id": "citation_actions",
        "elements": [
            {
                "type": "button",
                "action_id": "cite_1",
                "text": {
                    "type": "plain_text",
                    "text": "[1] The body of the citation",
                    "emoji": "true",
                },
                "style": "primary",  # Set citation as active
                "value": str(params),
            },
            {
                "type": "button",
                "action_id": "cite_2",
                "text": {
                    "type": "plain_text",
                    "text": "[2] The body of the citation",
                    "emoji": "true",
                },
                "style": None,  # Set citation as active
                "value": str(params),
            },
        ],
    }

    first_citation_body = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*First Citation Title*\n\n> First Citation Body"},
        "block_id": "citation_block",
    }

    second_citation_body = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*Second Citation Title*\n\n> Second Citation Body"},
        "block_id": "citation_block",
    }

    message = {
        "blocks": [citations, first_citation_body],
    }

    # perform operation
    open_citation("ABC", "123", message, params, mock_client)

    # assertions
    expected_blocks = [citations, second_citation_body]
    mock_client.chat_update.assert_called()
    mock_client.chat_update.assert_called_with(channel="ABC", ts="123", blocks=expected_blocks)


def test_create_response_body_no_error_without_citations(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    # perform operation
    _create_response_body(
        citations=[],
        feedback_data={},
        response_text="This is a response without a citation.[1]",
    )

    # assertions
    # no assertions as we are just checking it does not throw an error


def test_create_response_body_creates_body_without_citations(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    # perform operation
    response = _create_response_body(
        citations=[],
        feedback_data={},
        response_text="This is a response without a citation.",
    )

    # assertions
    assert len(response) > 0
    assert response[0]["type"] == "section"
    assert "This is a response without a citation." in response[0]["text"]["text"]


def test_create_response_body_update_body_with_citations(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    # perform operation
    response = _create_response_body(
        citations=[
            {
                "source_number": "1",
                "title": "Citation Title",
                "body": "Citation Body",
                "relevance_score": "0.95",
            }
        ],
        feedback_data={},
        response_text="This is a response with a citation.[1]",
    )

    # assertions
    assert len(response) > 1
    assert response[1]["type"] == "actions"
    assert response[1]["block_id"] == "citation_actions"

    citation_element = response[1]["elements"][0]
    assert citation_element["type"] == "button"
    assert citation_element["action_id"] == "cite_1"
    assert "[1] Citation Title" in citation_element["text"]["text"]


def test_create_response_body_creates_body_with_multiple_citations(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    # perform operation
    response = _create_response_body(
        citations=[
            {
                "source_number": "1",
                "title": "Citation Title",
                "body": "Citation Body",
                "relevance_score": "0.95",
            },
            {
                "source_number": "2",
                "title": "Citation Title",
                "body": "Citation Body",
                "relevance_score": "0.95",
            },
        ],
        feedback_data={},
        response_text="This is a response with a citation.[1]",
    )

    # assertions
    assert len(response) > 1
    assert response[1]["type"] == "actions"
    assert response[1]["block_id"] == "citation_actions"

    first_citation_element = response[1]["elements"][0]
    assert first_citation_element["type"] == "button"
    assert first_citation_element["action_id"] == "cite_1"
    assert "[1] Citation Title" in first_citation_element["text"]["text"]

    second_citation_element = response[1]["elements"][1]
    assert second_citation_element["type"] == "button"
    assert second_citation_element["action_id"] == "cite_2"
    assert "[2] Citation Title" in second_citation_element["text"]["text"]


def test_create_response_body_creates_body_ignoring_low_score_citations(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    # perform operation
    response = _create_response_body(
        citations=[
            {
                "source_number": "1",
                "title": "Citation Title",
                "body": "Citation Body",
                "relevance_score": "0.55",
            },
            {
                "source_number": "2",
                "title": "Citation Title",
                "body": "Citation Body",
                "relevance_score": "0.95",
            },
        ],
        feedback_data={},
        response_text="This is a response with a citation.[1]",
    )

    # assertions
    assert len(response) > 1
    assert response[1]["type"] == "actions"
    assert response[1]["block_id"] == "citation_actions"

    citation_elements = response[1]["elements"]
    assert len(citation_elements) == 1

    citation_element = citation_elements[0]
    assert citation_element["type"] == "button"
    assert citation_element["action_id"] == "cite_2"
    assert "[2] Citation Title" in citation_element["text"]["text"]


def test_create_response_body_update_body_with_reformatted_citations(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    # perform operation
    response = _create_response_body(
        citations=[
            {
                "source_number": "1",
                "title": "Citation Title",
                "body": "Citation Body",
                "relevance_score": "0.95",
            }
        ],
        feedback_data={},
        response_text="This is a response with a citation.[cit_1]",
    )

    # assertions
    assert len(response) > 1
    assert response[0]["type"] == "section"
    assert "This is a response with a citation.[1]" in response[0]["text"]["text"]


def test_create_response_body_creates_body_with_markdown_formatting(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    # perform operation
    response = _create_response_body(
        citations=[
            {
                "source_number": "1",
                "title": "Citation Title",
                "excerpt": "**Bold**, __italics__, *markdown italics*, and `code`.",
                "relevance_score": "0.95",
            }
        ],
        feedback_data={},
        response_text="This is a response with a citation.[1]",
    )

    # assertions
    assert len(response) > 1
    assert response[1]["type"] == "actions"
    assert response[1]["block_id"] == "citation_actions"

    citation_element = response[1]["elements"][0]
    citation_value = json.loads(citation_element["value"])

    assert "*Bold*, _italics_, _markdown italics_, and `code`." in citation_value.get("body")


def test_create_response_body_creates_body_with_lists(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    dirty_input = (
        "Header text"
        "\\n- Standard Dash"  # Literal \n + dash
        "-No Space Dash"  # Dash with no spacing
        "– En Dash"  # Unicode En-dash
        "— Em Dash"  # Unicode Em-dash
        "\n▪ Square Bullet"  # Real newline + Square
        " ‣ Triangle Bullet"  # Space + Triangle
        " ◦ Hollow Bullet"  # Space + Hollow
        "\\n• Standard Bullet"  # Literal \n + Bullet
    )

    # perform operation
    response = _create_response_body(
        citations=[
            {
                "source_number": "1",
                "title": "Citation Title",
                "excerpt": dirty_input,
                "relevance_score": "0.95",
            }
        ],
        feedback_data={},
        response_text="This is a response with a citation.[1]",
    )

    # assertions
    assert len(response) > 1
    assert response[1]["type"] == "actions"
    assert response[1]["block_id"] == "citation_actions"

    citation_element = response[1]["elements"][0]
    citation_value = json.loads(citation_element["value"])

    expected_output = (
        "Header text\n"
        "- Standard Dash\n"
        "- No Space Dash\n"
        "- En Dash\n"
        "- Em Dash\n"
        "- Square Bullet\n"
        "- Triangle Bullet\n"
        "- Hollow Bullet\n"
        "- Standard Bullet"
    )
    assert expected_output in citation_value.get("body")


def test_create_response_body_creates_body_without_encoding_errors(
    mock_get_parameter: Mock,
    mock_env: Mock,
):
    """Test regex text processing functionality within process_async_slack_event"""
    # delete and import module to test
    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]
    from app.slack.slack_events import _create_response_body

    # perform operation
    response = _create_response_body(
        citations=[
            {
                "source_number": "1",
                "title": "Citation Title",
                "excerpt": "» Tabbing Issue. â¢ Bullet point issue.",
                "relevance_score": "0.95",
            }
        ],
        feedback_data={},
        response_text="This is a response with a citation.[1]",
    )

    # assertions
    assert len(response) > 1
    assert response[1]["type"] == "actions"
    assert response[1]["block_id"] == "citation_actions"

    citation_element = response[1]["elements"][0]
    citation_value = json.loads(citation_element["value"])

    assert "Tabbing Issue.\n- Bullet point issue." in citation_value.get("body")


@patch("app.services.ai_processor.process_ai_query")
def test_create_citation_logs_citations(
    mock_process_ai_query: Mock,
    mock_logger,
):
    with patch("app.core.config.get_logger", return_value=mock_logger):
        # set up mocks
        mock_client = Mock()
        raw_citation = "1||This is the Title||This is the excerpt/ citation||0.99"
        mock_process_ai_query.return_value = {
            "text": "AI response" + "------" + f"<cit>{raw_citation}</cit>",
            "session_id": "session-123",
            "citations": [],
            "kb_response": {"output": {"text": "AI response"}},
        }

        # delete and import module to test
        if "app.slack.slack_events" in sys.modules:
            del sys.modules["app.slack.slack_events"]
        from app.slack.slack_events import process_slack_message

        # perform operation
        slack_event_data = {
            "text": "Answer",
            "user": "U456",
            "channel": "C789",
            "ts": "1234567890.123",
        }

        process_slack_message(event=slack_event_data, event_id="evt123", client=mock_client)

        # mock_logger.assert_has_calls([call.info("Found citation(s)", extra={"Raw Citations": [raw_citation]})])
        # assertions

        mock_logger.info.assert_any_call(
            "Found citation(s)", extra={"Raw Citations": ["1||This is the Title||This is the excerpt/ citation||0.99"]}
        )
        mock_logger.info.assert_any_call(
            "Parsed citation(s)",
            extra={
                "citations": [
                    {
                        "source_number": "1",
                        "title": "This is the Title",
                        "excerpt": "This is the excerpt/ citation",
                        "relevance_score": "0.99",
                    }
                ]
            },
        )
        # mock_logger.info.assert_called_with("Found citation(s)", extra={"Raw Citations": [raw_citation]})
