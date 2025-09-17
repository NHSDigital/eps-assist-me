import sys
from unittest.mock import Mock, patch


@patch("boto3.client")
def test_get_bedrock_knowledgebase_response(mock_boto_client, mock_env):
    """Test Bedrock knowledge base integration"""
    # set up mocks
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    mock_client.retrieve_and_generate.return_value = {"output": {"text": "bedrock response"}}

    # delete and import module to test
    if "app.services.bedrock" in sys.modules:
        del sys.modules["app.services.bedrock"]
    from app.services.bedrock import query_bedrock

    # perform operation
    result = query_bedrock("test query")

    # assertions
    mock_boto_client.assert_called_once_with(service_name="bedrock-agent-runtime", region_name="eu-west-2")
    mock_client.retrieve_and_generate.assert_called_once()
    assert result["output"]["text"] == "bedrock response"


@patch("boto3.client")
def test_query_bedrock_with_session(mock_boto_client, mock_env):
    """Test query_bedrock with existing session"""
    # set up mocks
    mock_client = Mock()
    mock_response = {"output": {"text": "response"}, "sessionId": "session123"}
    mock_client.retrieve_and_generate.return_value = mock_response
    mock_boto_client.return_value = mock_client

    # delete and import module to test
    if "app.services.bedrock" in sys.modules:
        del sys.modules["app.services.bedrock"]
    from app.services.bedrock import query_bedrock

    # perform operation
    result = query_bedrock("test query", session_id="existing_session")

    # assertions
    assert result == mock_response
    call_args = mock_client.retrieve_and_generate.call_args[1]
    assert call_args["sessionId"] == "existing_session"


@patch("boto3.client")
def test_query_bedrock_without_session(mock_boto_client, mock_env):
    """Test query_bedrock without session"""
    # set up mocks
    mock_client = Mock()
    mock_response = {"output": {"text": "response"}, "sessionId": "new_session"}
    mock_client.retrieve_and_generate.return_value = mock_response
    mock_boto_client.return_value = mock_client

    # delete and import module to test
    if "app.services.bedrock" in sys.modules:
        del sys.modules["app.services.bedrock"]
    from app.services.bedrock import query_bedrock

    # perform operation
    result = query_bedrock("test query")

    # assertions
    assert result == mock_response
    call_args = mock_client.retrieve_and_generate.call_args[1]
    assert "sessionId" not in call_args
