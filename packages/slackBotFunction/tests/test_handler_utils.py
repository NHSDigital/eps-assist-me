import sys
from unittest.mock import Mock, patch
from slack_sdk.errors import SlackApiError
from botocore.exceptions import ClientError


@patch("app.services.dynamo.get_state_information")
def test_is_latest_message_matching_ts(mock_get_state_information: Mock):
    """Test _is_latest_message function logic"""
    # setup mocks
    mock_get_state_information.return_value = {"Item": {"latest_message_ts": "123"}}

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import is_latest_message

    # perform operation
    result = is_latest_message("conv-key", "123")

    # assertions
    assert result is True


@patch("app.services.dynamo.get_state_information")
def test_is_latest_message_non_matching_ts(mock_get_state_information: Mock):
    """Test _is_latest_message function logic"""
    # setup mocks
    mock_get_state_information.return_value = {"Item": {"latest_message_ts": "456"}}

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import is_latest_message

    # perform operation
    result = is_latest_message("conv-key", "123")

    # assertions
    assert result is False


@patch("app.services.dynamo.get_state_information")
def test_is_latest_message_no_item_in_response(mock_get_state_information: Mock):
    """Test _is_latest_message function logic"""
    # setup mocks
    mock_get_state_information.return_value = {}

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import is_latest_message

    # perform operation
    result = is_latest_message("conv-key", "123")

    # assertions
    assert result is False


@patch("app.services.dynamo.get_state_information")
def test_is_latest_message_exception(mock_get_state_information: Mock):
    """Test _is_latest_message function logic"""
    # setup mocks
    mock_get_state_information.side_effect = Exception("DB error")

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import is_latest_message

    # perform operation
    result = is_latest_message("conv-key", "123")

    # assertions
    assert result is False


def test_gate_common_missing_event_id(mock_env: Mock):
    """Test _gate_common with missing event_id"""
    # setup mocks

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import gate_common

    # perform operation
    event = {"text": "test"}
    body = {}  # Missing event_id

    result = gate_common(event, body)

    # assertions
    assert result is None


def test_gate_common_bot_message(mock_env: Mock):
    """Test _gate_common with bot message"""
    # setup mocks

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import gate_common

    # perform operation
    event = {"text": "test", "bot_id": "B123"}
    body = {"event_id": "evt123"}

    result = gate_common(event, body)

    # assertions
    assert result is None


def test_gate_common_subtype_message(mock_env: Mock):
    """Test _gate_common with subtype message"""
    # setup mocks

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import gate_common

    # perform operation
    event = {"text": "test", "subtype": "message_changed"}
    body = {"event_id": "evt123"}

    result = gate_common(event, body)

    # assertions
    assert result is None


def test_strip_mentions_with_alias(mock_env: Mock):
    """Test _strip_mentions with user alias"""
    # setup mocks
    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import strip_mentions

    # perform operation
    text = "<@U123|username> hello world"
    result = strip_mentions(text)

    # assertions
    assert result == "hello world"


def test_gate_common_empty_vars(mock_env: Mock):
    """Test that empty feedback doesn't crash"""
    # set up mocks

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.slack.slack_handlers import gate_common

    # perform operation
    result = gate_common({}, {})

    # assertions
    assert result is None


def test_gate_common_populated_vars(mock_env: Mock):
    """Test that empty feedback doesn't crash"""
    # set up mocks

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.slack.slack_handlers import gate_common

    # perform operation
    result = gate_common({"bot_id": "B123"}, {"event_id": "evt123"})

    # assertions
    assert result is None


def test_strip_mentions(mock_env: Mock):
    """Test that empty feedback doesn't crash"""
    # set up mocks

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.slack.slack_handlers import strip_mentions

    # perform operation
    result = strip_mentions("<@U123> hello world")

    # assertions
    assert result == "hello world"


def test_extract_key_and_root(mock_env: Mock):
    """Test that empty feedback doesn't crash"""
    # set up mocks

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.slack.slack_handlers import conversation_key_and_root

    # perform operation
    event = {"channel": "D123", "ts": "456", "channel_type": "im"}
    key, root = conversation_key_and_root(event)

    # assertions
    assert key == "dm#D123"
    assert root == "456"


@patch("slack_sdk.WebClient")
def test_respond_with_eyes_on_success(
    mock_webclient: Mock,
    mock_env: Mock,
    mock_get_parameter: Mock,
):
    """Test that respond with eyes"""
    # set up mocks
    mock_client = Mock()
    mock_client.reactions_add.return_value = {"success"}
    mock_webclient.return_value = mock_client

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.slack.slack_handlers import respond_with_eyes

    # perform operation
    event = {"channel": "D123", "ts": "456", "channel_type": "im"}
    respond_with_eyes(event)

    # assertions
    # just need to make sure it does not error


@patch("slack_sdk.WebClient")
def test_respond_with_eyes_on_failure(
    mock_webclient: Mock,
    mock_env: Mock,
    mock_get_parameter: Mock,
):
    """Test that respond with eyes"""
    # set up mocks
    mock_client = Mock()
    mock_client.reactions_add.side_effect = SlackApiError("There was a problem", 500)
    mock_webclient.return_value = mock_client

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.slack.slack_handlers import respond_with_eyes

    # perform operation
    event = {"channel": "D123", "ts": "456", "channel_type": "im"}
    respond_with_eyes(event)

    # assertions
    # just need to make sure it does not error


@patch("app.services.dynamo.store_state_information")
def test_is_duplicate_event_returns_true_when_conditional_check_fails(
    mock_store_state_information: Mock,
    mock_env: Mock,
):
    """Test duplicate event detection with conditional put"""
    # set up mocks
    error = ClientError(error_response={"Error": {"Code": "ConditionalCheckFailedException"}}, operation_name="PutItem")
    mock_store_state_information.side_effect = error

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import is_duplicate_event

    # perform operation
    result = is_duplicate_event("test-event")

    # assertions
    assert result is True


@patch("app.services.dynamo.store_state_information")
def test_is_duplicate_event_client_error(
    mock_store_state_information: Mock,
    mock_env: Mock,
):
    """Test is_duplicate_event handles other ClientError"""
    # set up mocks
    error = ClientError(error_response={"Error": {"Code": "SomeOtherError"}}, operation_name="PutItem")
    mock_store_state_information.side_effect = error

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import is_duplicate_event

    # perform operation
    result = is_duplicate_event("test-event")

    # assertions
    assert result is False


@patch("app.services.dynamo.store_state_information")
def test_is_duplicate_event_no_item(
    mock_store_state_information: Mock,
    mock_env: Mock,
):
    """Test is_duplicate_event when no item exists (successful put)"""
    # set up mocks

    # delete and import module to test
    if "app.utils.handler_utils" in sys.modules:
        del sys.modules["app.utils.handler_utils"]
    from app.utils.handler_utils import is_duplicate_event

    # perform operation
    result = is_duplicate_event("test-event")

    # assertions
    assert result is False
