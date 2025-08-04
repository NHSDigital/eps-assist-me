import pytest
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
    return client


@patch("app.wait_for_index_aoss")
@patch("app.get_opensearch_client")
def test_create_and_wait_for_index_new(mock_get_client, mock_wait, mock_opensearch_client):
    """Test creating a new index"""
    mock_get_client.return_value = mock_opensearch_client
    mock_wait.return_value = True

    from app import create_and_wait_for_index

    create_and_wait_for_index(mock_opensearch_client, "test-index")

    mock_opensearch_client.indices.exists.assert_called_with(index="test-index")
    mock_opensearch_client.indices.create.assert_called_once()


@patch("app.wait_for_index_aoss")
@patch("app.get_opensearch_client")
def test_create_and_wait_for_index_exists(mock_get_client, mock_wait, mock_opensearch_client):
    """Test with existing index"""
    mock_opensearch_client.indices.exists.return_value = True
    mock_get_client.return_value = mock_opensearch_client
    mock_wait.return_value = True

    from app import create_and_wait_for_index

    create_and_wait_for_index(mock_opensearch_client, "test-index")

    mock_opensearch_client.indices.create.assert_not_called()


def test_wait_for_index_aoss_success():
    """Test successful index wait"""
    mock_client = Mock()
    mock_client.indices.exists.return_value = True
    mock_client.indices.get_mapping.return_value = {"test-index": {"mappings": {}}}

    from app import wait_for_index_aoss

    result = wait_for_index_aoss(mock_client, "test-index", timeout=1, poll_interval=0.1)

    assert result is True


def test_extract_parameters_cloudformation():
    """Test parameter extraction from CloudFormation event"""
    from app import extract_parameters

    event = {
        "ResourceProperties": {"Endpoint": "test-endpoint", "IndexName": "test-index"},
        "RequestType": "Create",
    }

    params = extract_parameters(event)

    assert params["endpoint"] == "test-endpoint"
    assert params["index_name"] == "test-index"
    assert params["request_type"] == "Create"


def test_extract_parameters_direct():
    """Test parameter extraction from direct invocation"""
    from app import extract_parameters

    event = {
        "Endpoint": "test-endpoint",
        "IndexName": "test-index",
        "RequestType": "Create",
    }

    params = extract_parameters(event)

    assert params["endpoint"] == "test-endpoint"
    assert params["index_name"] == "test-index"
    assert params["request_type"] == "Create"


@patch("app.get_opensearch_client")
@patch("app.create_and_wait_for_index")
def test_handler_create(mock_create_wait, mock_get_client, lambda_context):
    """Test handler for Create request"""
    from app import handler

    event = {
        "RequestType": "Create",
        "Endpoint": "test-endpoint",
        "IndexName": "test-index",
    }

    result = handler(event, lambda_context)

    mock_create_wait.assert_called_once()
    assert result["Status"] == "SUCCESS"
    assert result["PhysicalResourceId"] == "index-test-index"


@patch("app.get_opensearch_client")
def test_handler_delete(mock_get_client, lambda_context):
    """Test handler for Delete request"""
    mock_client = Mock()
    mock_client.indices.exists.return_value = True
    mock_get_client.return_value = mock_client

    from app import handler

    event = {
        "RequestType": "Delete",
        "Endpoint": "test-endpoint",
        "IndexName": "test-index",
        "PhysicalResourceId": "index-test-index",
    }

    result = handler(event, lambda_context)

    mock_client.indices.delete.assert_called_once_with(index="test-index")
    assert result["Status"] == "SUCCESS"


def test_handler_invalid_request_type(lambda_context):
    """Test handler with invalid request type"""
    from app import handler

    event = {
        "RequestType": "Invalid",
        "Endpoint": "test-endpoint",
        "IndexName": "test-index",
    }

    with pytest.raises(ValueError, match="Invalid request type"):
        handler(event, lambda_context)


def test_handler_missing_parameters(lambda_context):
    """Test handler with missing parameters"""
    from app import handler

    event = {
        "RequestType": "Create"
        # Missing Endpoint and IndexName
    }

    with pytest.raises(ValueError, match="Missing required parameters"):
        handler(event, lambda_context)
