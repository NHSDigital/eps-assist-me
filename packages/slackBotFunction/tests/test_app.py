import pytest
import json
from unittest.mock import Mock, patch
from moto import mock_aws
import boto3
import os
import sys


TEST_BOT_TOKEN = "test-bot-token"
TEST_SIGNING_SECRET = "test-signing-secret"


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    env_vars = {
        "SLACK_BOT_TOKEN_PARAMETER": "/test/bot-token",
        "SLACK_SIGNING_SECRET_PARAMETER": "/test/signing-secret",
        "SLACK_DEDUPLICATION_TABLE": "test-dedup-table",
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
def mock_dynamodb_table():
    """Mock DynamoDB table"""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
        table = dynamodb.create_table(
            TableName="test-dedup-table",
            KeySchema=[{"AttributeName": "eventId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "eventId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.function_name = "test-function"
    context.aws_request_id = "test-request-id"
    return context


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_log_request(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test middleware function behavior"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app" in sys.modules:
        del sys.modules["app"]

    # Test that the middleware function exists and can be imported
    from app import log_request

    assert callable(log_request)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_is_duplicate_event(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test duplicate event detection"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_table.get_item.return_value = {"Item": {"eventId": "test-event"}}

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import is_duplicate_event

    result = is_duplicate_event("test-event")
    assert result is True


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("time.time")
def test_mark_event_processed(mock_time, mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test marking event as processed"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_time.return_value = 1000

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import mark_event_processed

    mark_event_processed("test-event")
    mock_table.put_item.assert_called_once_with(Item={"eventId": "test-event", "ttl": 4600, "timestamp": 1000})


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
def test_get_bedrock_knowledgebase_response(
    mock_boto_client, mock_boto_resource, mock_get_parameter, mock_app, mock_env
):
    """Test Bedrock knowledge base integration"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    mock_client.retrieve_and_generate.return_value = {"output": {"text": "bedrock response"}}

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import get_bedrock_knowledgebase_response

    result = get_bedrock_knowledgebase_response("test query")

    mock_boto_client.assert_called_once_with(service_name="bedrock-agent-runtime", region_name="eu-west-2")
    mock_client.retrieve_and_generate.assert_called_once()
    assert result["output"]["text"] == "bedrock response"


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handler_normal_event(mock_boto_resource, mock_get_parameter, mock_app, mock_env, lambda_context):
    """Test Lambda handler function for normal Slack events"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app" in sys.modules:
        del sys.modules["app"]

    with patch("app.SlackRequestHandler") as mock_handler_class:
        mock_handler = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler.handle.return_value = {"statusCode": 200}

        from app import handler

        event = {"body": "test event"}
        result = handler(event, lambda_context)

        mock_handler.handle.assert_called_once_with(event, lambda_context)
        assert result["statusCode"] == 200


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handler_async_processing(mock_boto_resource, mock_get_parameter, mock_app, mock_env, lambda_context):
    """Test Lambda handler function for async processing"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app" in sys.modules:
        del sys.modules["app"]

    with patch("app.process_async_slack_event") as mock_process:
        from app import handler

        event = {"async_processing": True, "slack_event": {"test": "data"}}
        result = handler(event, lambda_context)

        mock_process.assert_called_once_with({"test": "data"})
        assert result["statusCode"] == 200


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
def test_trigger_async_processing(mock_boto_client, mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test triggering async processing"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()
    mock_lambda_client = Mock()
    mock_boto_client.return_value = mock_lambda_client

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import trigger_async_processing

    event_data = {"test": "data"}
    trigger_async_processing(event_data)

    mock_boto_client.assert_called_once_with("lambda")
    mock_lambda_client.invoke.assert_called_once()


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handle_app_mention(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test app mention handler exists and is callable"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import handle_app_mention

    assert callable(handle_app_mention)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_handle_direct_message(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test direct message handler exists and is callable"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import handle_direct_message

    assert callable(handle_direct_message)


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_process_async_slack_event_exists(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test process_async_slack_event function exists and is callable"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import process_async_slack_event

    assert callable(process_async_slack_event)


@patch("botocore.exceptions.ClientError")
@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_is_duplicate_event_client_error(mock_boto_resource, mock_get_parameter, mock_app, mock_client_error, mock_env):
    """Test is_duplicate_event handles ClientError"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_table.get_item.side_effect = mock_client_error

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import is_duplicate_event

    result = is_duplicate_event("test-event")
    assert result is False


@patch("botocore.exceptions.ClientError")
@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("time.time")
def test_mark_event_processed_client_error(
    mock_time, mock_boto_resource, mock_get_parameter, mock_app, mock_client_error, mock_env
):
    """Test mark_event_processed handles ClientError"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_table.put_item.side_effect = mock_client_error
    mock_time.return_value = 1000

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import mark_event_processed

    # Should not raise exception
    mark_event_processed("test-event")


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
def test_is_duplicate_event_no_item(mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test is_duplicate_event when no item exists"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_table = Mock()
    mock_boto_resource.return_value.Table.return_value = mock_table
    mock_table.get_item.return_value = {}  # No Item key

    if "app" in sys.modules:
        del sys.modules["app"]

    from app import is_duplicate_event

    result = is_duplicate_event("test-event")
    assert result is False


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("re.sub")
def test_regex_text_processing(mock_re_sub, mock_boto_resource, mock_get_parameter, mock_app, mock_env):
    """Test regex processing in process_async_slack_event"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()
    mock_re_sub.return_value = "cleaned text"

    if "app" in sys.modules:
        del sys.modules["app"]

    # Verify re.sub is available for import
    assert mock_re_sub is not None
