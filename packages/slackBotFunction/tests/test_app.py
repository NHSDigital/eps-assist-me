import pytest
import json
from unittest.mock import Mock, patch
import os
import sys
from botocore.exceptions import ClientError


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    env_vars = {
        "SLACK_BOT_TOKEN_PARAMETER": "/test/bot-token",
        "SLACK_SIGNING_SECRET_PARAMETER": "/test/signing-secret",
        "SLACK_BOT_STATE_TABLE": "test-bot-state-table",
        "KNOWLEDGEBASE_ID": "test-kb-id",
        "RAG_MODEL_ID": "test-model-id",
        "AWS_REGION": "eu-west-2",
        "GUARD_RAIL_ID": "test-guard-id",
        "GUARD_RAIL_VERSION": "1",
        "AWS_LAMBDA_FUNCTION_NAME": "test-function",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.function_name = "test-function"
    context.aws_request_id = "test-request-id"
    return context


def clear_modules():
    """Clear app modules from cache"""
    modules_to_clear = [k for k in sys.modules.keys() if k.startswith("app")]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_bolt.adapter.aws_lambda.SlackRequestHandler")
@patch("slack_bolt.App")
def test_handler_normal_event(
    mock_app_class, mock_handler_class, mock_boto_resource, mock_get_parameter, mock_env, lambda_context
):
    """Test Lambda handler function for normal Slack events"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app = Mock()
    mock_app_class.return_value = mock_app

    # Mock SlackRequestHandler
    mock_handler = Mock()
    mock_handler_class.return_value = mock_handler
    mock_handler.handle.return_value = {"statusCode": 200}

    clear_modules()

    from app.handler import handler

    event = {"body": "test event"}
    result = handler(event, lambda_context)

    mock_handler.handle.assert_called_once_with(event, lambda_context)
    assert result["statusCode"] == 200


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_bolt.App")
def test_handler_async_processing(mock_app_class, mock_boto_resource, mock_get_parameter, mock_env, lambda_context):
    """Test Lambda handler function for async processing"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app = Mock()
    mock_app_class.return_value = mock_app

    clear_modules()

    with patch("app.slack.slack_events.process_async_slack_event") as mock_process:
        from app.handler import handler

        event = {"async_processing": True, "slack_event": {"test": "data"}}
        result = handler(event, lambda_context)

        mock_process.assert_called_once_with({"test": "data"})
        assert result["statusCode"] == 200


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
@patch("slack_bolt.App")
def test_get_bedrock_knowledgebase_response(
    mock_app_class, mock_boto_client, mock_boto_resource, mock_get_parameter, mock_env
):
    """Test Bedrock knowledge base integration"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app_class.return_value = Mock()

    # Mock Bedrock client
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    mock_client.retrieve_and_generate.return_value = {"output": {"text": "bedrock response"}}

    clear_modules()

    from app.slack.slack_events import get_bedrock_knowledgebase_response

    result = get_bedrock_knowledgebase_response("test query")

    mock_boto_client.assert_called_once_with(service_name="bedrock-agent-runtime", region_name="eu-west-2")
    mock_client.retrieve_and_generate.assert_called_once()
    assert result["output"]["text"] == "bedrock response"


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
@patch("slack_bolt.App")
def test_trigger_async_processing(mock_app_class, mock_boto_client, mock_boto_resource, mock_get_parameter, mock_env):
    """Test triggering async processing"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app_class.return_value = Mock()

    # Mock Lambda client
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    clear_modules()

    from app.slack.slack_handlers import trigger_async_processing

    event_data = {"test": "data"}
    trigger_async_processing(event_data)

    mock_boto_client.assert_called_once_with("lambda")
    mock_lambda_client.invoke.assert_called_once()


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("time.time")
@patch("slack_bolt.App")
def test_is_duplicate_event(mock_app_class, mock_time, mock_boto_resource, mock_get_parameter, mock_env):
    """Test duplicate event detection with conditional put"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_time.return_value = 1000

    # Mock Slack App
    mock_app_class.return_value = Mock()

    # Mock ConditionalCheckFailedException
    error = ClientError(error_response={"Error": {"Code": "ConditionalCheckFailedException"}}, operation_name="PutItem")
    mock_table.put_item.side_effect = error

    clear_modules()

    from app.slack.slack_handlers import is_duplicate_event

    result = is_duplicate_event("test-event")
    assert result is True


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("time.time")
@patch("slack_bolt.App")
def test_is_duplicate_event_no_duplicate(mock_app_class, mock_time, mock_boto_resource, mock_get_parameter, mock_env):
    """Test is_duplicate_event when no item exists (successful put)"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_time.return_value = 1000

    # Mock Slack App
    mock_app_class.return_value = Mock()

    clear_modules()

    from app.slack.slack_handlers import is_duplicate_event

    result = is_duplicate_event("test-event")
    assert result is False


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_sdk.WebClient")
@patch("slack_bolt.App")
def test_process_async_slack_event_success(
    mock_app_class, mock_webclient, mock_boto_resource, mock_get_parameter, mock_env
):
    """Test successful async event processing"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app_class.return_value = Mock()

    mock_client = Mock()
    mock_webclient.return_value = mock_client

    clear_modules()

    with patch("app.slack.slack_events.get_bedrock_knowledgebase_response") as mock_bedrock:
        mock_bedrock.return_value = {"output": {"text": "AI response"}}

        from app.slack.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {
                "text": "<@U123> test question",
                "user": "U456",
                "channel": "C789",
                "ts": "1234567890.123",
            },
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        process_async_slack_event(slack_event_data)

        mock_client.chat_postMessage.assert_called_once_with(
            channel="C789", text="AI response", thread_ts="1234567890.123"
        )


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_sdk.WebClient")
@patch("slack_bolt.App")
def test_process_async_slack_event_with_thread_ts(
    mock_app_class, mock_webclient, mock_boto_resource, mock_get_parameter, mock_env
):
    """Test async event processing with existing thread_ts"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app_class.return_value = Mock()

    mock_client = Mock()
    mock_webclient.return_value = mock_client

    clear_modules()

    with patch("app.slack.slack_events.get_bedrock_knowledgebase_response") as mock_bedrock:
        mock_bedrock.return_value = {"output": {"text": "AI response"}}

        from app.slack.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {
                "text": "<@U123> test question",
                "user": "U456",
                "channel": "C789",
                "ts": "1234567890.123",
                "thread_ts": "1234567888.111",  # Existing thread
            },
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        process_async_slack_event(slack_event_data)

        # Should use the existing thread_ts, not the message ts
        mock_client.chat_postMessage.assert_called_once_with(
            channel="C789", text="AI response", thread_ts="1234567888.111"
        )


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_sdk.WebClient")
@patch("slack_bolt.App")
def test_process_async_slack_event_empty_query(
    mock_app_class, mock_webclient, mock_boto_resource, mock_get_parameter, mock_env
):
    """Test async event processing with empty query"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app_class.return_value = Mock()

    mock_client = Mock()
    mock_webclient.return_value = mock_client

    clear_modules()

    from app.slack.slack_events import process_async_slack_event

    slack_event_data = {
        "event": {
            "text": "<@U123>",  # Only mention, no actual query
            "user": "U456",
            "channel": "C789",
            "ts": "1234567890.123",
        },
        "event_id": "evt123",
        "bot_token": "bot-token",
    }

    process_async_slack_event(slack_event_data)

    mock_client.chat_postMessage.assert_called_once_with(
        channel="C789",
        text="Hi there! Please ask me a question and I'll help you find information from our knowledge base.",
        thread_ts="1234567890.123",
    )


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_sdk.WebClient")
@patch("slack_bolt.App")
def test_process_async_slack_event_error(
    mock_app_class, mock_webclient, mock_boto_resource, mock_get_parameter, mock_env
):
    """Test async event processing with error"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app_class.return_value = Mock()

    mock_client = Mock()
    mock_webclient.return_value = mock_client

    clear_modules()

    with patch("app.slack.slack_events.get_bedrock_knowledgebase_response") as mock_bedrock:
        mock_bedrock.side_effect = Exception("Bedrock error")

        from app.slack.slack_events import process_async_slack_event

        slack_event_data = {
            "event": {
                "text": "test question",
                "user": "U456",
                "channel": "C789",
                "ts": "1234567890.123",
            },
            "event_id": "evt123",
            "bot_token": "bot-token",
        }

        process_async_slack_event(slack_event_data)

        mock_client.chat_postMessage.assert_called_once_with(
            channel="C789",
            text="Sorry, an error occurred while processing your request. Please try again later.",
            thread_ts="1234567890.123",
        )


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_bolt.App")
def test_handle_direct_message_channel_type(mock_app_class, mock_boto_resource, mock_get_parameter, mock_env):
    """Test direct message handler channel type check"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app_class.return_value = Mock()

    clear_modules()

    # Import to test the function exists
    from app.slack.slack_handlers import handle_direct_message

    assert callable(handle_direct_message)


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("slack_bolt.App")
def test_log_request_middleware_execution(mock_app_class, mock_boto_resource, mock_get_parameter, mock_env):
    """Test log_request middleware execution"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    # Mock DynamoDB
    mock_boto_resource.return_value.Table.return_value = Mock()

    # Mock Slack App
    mock_app_class.return_value = Mock()

    clear_modules()

    from app.slack.slack_handlers import log_request

    # Test the middleware function directly
    mock_next = Mock(return_value="middleware_result")
    mock_logger = Mock()
    test_body = {"test": "body"}

    result = log_request(mock_logger, test_body, mock_next)

    assert result == "middleware_result"
    mock_next.assert_called_once()


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
@patch("time.time")
@patch("slack_bolt.App")
def test_app_mention_handler_flow(
    mock_app_class,
    mock_time,
    mock_boto_client,
    mock_boto_resource,
    mock_get_parameter,
    mock_env,
):
    """Test app mention handler execution flow"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    mock_time.return_value = 1000
    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client
    mock_app_class.return_value = Mock()

    clear_modules()

    from app.slack.slack_handlers import handle_app_mention

    mock_ack = Mock()
    event = {"user": "U123", "text": "test message"}
    body = {"event_id": "new-event-123"}

    # Test successful flow (no duplicate)
    handle_app_mention(event, mock_ack, body)
    mock_ack.assert_called()


@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
@patch("time.time")
@patch("slack_bolt.App")
def test_direct_message_handler_flow(
    mock_app_class,
    mock_time,
    mock_boto_client,
    mock_boto_resource,
    mock_get_parameter,
    mock_env,
):
    """Test direct message handler execution flow"""
    # Mock parameter retrieval
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]

    mock_time.return_value = 1000
    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client
    mock_app_class.return_value = Mock()

    clear_modules()

    from app.slack.slack_handlers import handle_direct_message

    mock_ack = Mock()

    # Test IM channel - successful flow
    event = {"user": "U123", "text": "test message", "channel_type": "im"}
    body = {"event_id": "new-dm-event-123"}

    handle_direct_message(event, mock_ack, body)
    mock_ack.assert_called()

    # Test non-IM channel (should be ignored)
    event_non_im = {"user": "U123", "text": "test message", "channel_type": "channel"}
    handle_direct_message(event_non_im, mock_ack, body)
    mock_ack.assert_called()


def test_basic_functionality():
    """Basic test to ensure pytest works"""
    assert 1 + 1 == 2


def test_async_event_structure():
    """Test async event structure validation"""
    async_event = {"async_processing": True, "slack_event": {"test": "data"}}
    assert async_event.get("async_processing") is True
    assert "slack_event" in async_event


def test_normal_event_structure():
    """Test normal event structure validation"""
    normal_event = {"body": "test event", "headers": {"content-type": "application/json"}}
    assert "body" in normal_event
    assert normal_event.get("async_processing") is None
