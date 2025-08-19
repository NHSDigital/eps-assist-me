import pytest
import json
from unittest.mock import Mock, patch
import os


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    env_vars = {"AWS_REGION": "eu-west-2", "INDEX_NAME": "test-index"}
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.function_name = "test-function"
    context.aws_request_id = "test-request-id"
    return context


@pytest.fixture
def mock_opensearch_client():
    """Mock OpenSearch client"""
    client = Mock()
    client.indices.exists.return_value = False
    client.indices.create.return_value = {"acknowledged": True}
    client.indices.get_mapping.return_value = {"test-index": {"mappings": {}}}
    client.indices.delete.return_value = {"acknowledged": True}
    return client


@patch("app.handler.boto3.Session")
def test_get_opensearch_client(mock_session):
    """Test OpenSearch client creation"""
    mock_credentials = Mock()
    mock_session.return_value.get_credentials.return_value = mock_credentials

    from app.handler import get_opensearch_client

    client = get_opensearch_client("test-endpoint.aoss.amazonaws.com")
    assert client is not None
    mock_session.assert_called_once()


@patch("app.handler.time.sleep")
@patch("app.handler.time.time")
def test_wait_for_index_aoss_success(mock_time, mock_sleep, mock_opensearch_client):
    """Test successful index waiting"""
    mock_time.side_effect = [0, 1, 2]  # Simulate time progression
    mock_opensearch_client.indices.exists.return_value = True
    mock_opensearch_client.indices.get_mapping.return_value = {"test-index": {"mappings": {}}}

    from app.handler import wait_for_index_aoss

    result = wait_for_index_aoss(mock_opensearch_client, "test-index", timeout=10)
    assert result is True


@patch("app.handler.time.sleep")
@patch("app.handler.time.time")
def test_wait_for_index_aoss_timeout(mock_time, mock_sleep, mock_opensearch_client):
    """Test index waiting timeout"""
    mock_time.side_effect = [0, 5, 10, 15]  # Simulate timeout
    mock_opensearch_client.indices.exists.return_value = False

    from app.handler import wait_for_index_aoss

    result = wait_for_index_aoss(mock_opensearch_client, "test-index", timeout=10)
    assert result is False


@patch("app.handler.wait_for_index_aoss")
def test_create_and_wait_for_index_new(mock_wait, mock_opensearch_client):
    """Test creating a new index"""
    mock_wait.return_value = True
    mock_opensearch_client.indices.exists.return_value = False

    from app.handler import create_and_wait_for_index

    create_and_wait_for_index(mock_opensearch_client, "test-index")

    mock_opensearch_client.indices.exists.assert_called_with(index="test-index")
    mock_opensearch_client.indices.create.assert_called_once()


@patch("app.handler.wait_for_index_aoss")
def test_create_and_wait_for_index_exists(mock_wait, mock_opensearch_client):
    """Test with existing index"""
    mock_wait.return_value = True
    mock_opensearch_client.indices.exists.return_value = True

    from app.handler import create_and_wait_for_index

    create_and_wait_for_index(mock_opensearch_client, "test-index")

    mock_opensearch_client.indices.create.assert_not_called()


def test_extract_parameters_cloudformation():
    """Test parameter extraction from CloudFormation event"""
    from app.handler import extract_parameters

    event = {"ResourceProperties": {"Endpoint": "test-endpoint", "IndexName": "test-index"}, "RequestType": "Create"}

    result = extract_parameters(event)
    assert result["endpoint"] == "test-endpoint"
    assert result["index_name"] == "test-index"
    assert result["request_type"] == "Create"


def test_extract_parameters_direct():
    """Test parameter extraction from direct event"""
    from app.handler import extract_parameters

    event = {"Endpoint": "test-endpoint", "IndexName": "test-index", "RequestType": "Delete"}

    result = extract_parameters(event)
    assert result["endpoint"] == "test-endpoint"
    assert result["index_name"] == "test-index"
    assert result["request_type"] == "Delete"


@patch("app.handler.get_opensearch_client")
@patch("app.handler.create_and_wait_for_index")
def test_handler_create(mock_create_wait, mock_get_client, lambda_context):
    """Test handler for Create request"""
    mock_get_client.return_value = Mock()

    from app.handler import handler

    event = {
        "RequestType": "Create",
        "Endpoint": "test-endpoint",
        "IndexName": "test-index",
    }

    result = handler(event, lambda_context)

    mock_create_wait.assert_called_once()
    assert result["Status"] == "SUCCESS"
    assert result["PhysicalResourceId"] == "index-test-index"


@patch("app.handler.get_opensearch_client")
def test_handler_delete(mock_get_client, mock_opensearch_client, lambda_context):
    """Test handler for Delete request"""
    mock_get_client.return_value = mock_opensearch_client
    mock_opensearch_client.indices.exists.return_value = True

    from app.handler import handler

    event = {
        "RequestType": "Delete",
        "Endpoint": "test-endpoint",
        "IndexName": "test-index",
        "PhysicalResourceId": "existing-resource-id",
    }

    result = handler(event, lambda_context)

    mock_opensearch_client.indices.delete.assert_called_once_with(index="test-index")
    assert result["Status"] == "SUCCESS"
    assert result["PhysicalResourceId"] == "existing-resource-id"


@patch("app.handler.get_opensearch_client")
def test_handler_missing_parameters(mock_get_client, lambda_context):
    """Test handler with missing parameters"""
    from app.handler import handler

    event = {"RequestType": "Create"}  # Missing required parameters

    with pytest.raises(ValueError, match="Missing required parameters"):
        handler(event, lambda_context)


@patch("app.handler.get_opensearch_client")
def test_handler_with_payload(mock_get_client, mock_opensearch_client, lambda_context):
    """Test handler with JSON payload"""
    mock_get_client.return_value = mock_opensearch_client
    mock_opensearch_client.indices.exists.return_value = True

    from app.handler import handler

    payload_event = {"RequestType": "Delete", "Endpoint": "test-endpoint", "IndexName": "test-index"}

    event = {"Payload": json.dumps(payload_event)}

    result = handler(event, lambda_context)

    assert result["Status"] == "SUCCESS"
