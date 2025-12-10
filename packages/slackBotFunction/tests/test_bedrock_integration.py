import sys
from unittest.mock import Mock, patch


@patch("app.services.prompt_loader.load_prompt")
@patch("boto3.client")
def test_get_bedrock_knowledgebase_response(mock_boto_client: Mock, mock_load_prompt: Mock, mock_env: Mock):
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
    mock_load_prompt.assert_called_once_with("test-rag-prompt", "DRAFT")
    mock_boto_client.assert_called_once_with(service_name="bedrock-agent-runtime", region_name="eu-west-2")
    mock_client.retrieve_and_generate.assert_called_once()
    assert result["output"]["text"] == "bedrock response"


@patch("app.services.prompt_loader.load_prompt")
@patch("boto3.client")
def test_query_bedrock_with_session(mock_boto_client: Mock, mock_load_prompt: Mock, mock_env: Mock):
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
    mock_load_prompt.assert_called_once_with("test-rag-prompt", "DRAFT")
    assert result == mock_response
    call_args = mock_client.retrieve_and_generate.call_args[1]
    assert call_args["sessionId"] == "existing_session"


@patch("app.services.prompt_loader.load_prompt")
@patch("boto3.client")
def test_query_bedrock_without_session(mock_boto_client: Mock, mock_load_prompt: Mock, mock_env: Mock):
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
    mock_load_prompt.assert_called_once_with("test-rag-prompt", "DRAFT")
    assert result == mock_response
    call_args = mock_client.retrieve_and_generate.call_args[1]
    assert "sessionId" not in call_args


@patch("app.services.prompt_loader.load_prompt")
@patch("boto3.client")
def test_query_bedrock_check_prompt(mock_boto_client: Mock, mock_load_prompt: Mock, mock_env: Mock):
    """Test query_bedrock prompt loading"""
    # set up mocks
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    mock_client.retrieve_and_generate.return_value = {"output": {"text": "response"}}
    mock_load_prompt.return_value = {"prompt_text": "Test prompt template", "inference_config": {}}

    # delete and import module to test
    if "app.services.bedrock" in sys.modules:
        del sys.modules["app.services.bedrock"]
    from app.services.bedrock import query_bedrock

    # perform operation
    result = query_bedrock("test query")

    # assertions
    mock_load_prompt.assert_called_once_with("test-rag-prompt", "DRAFT")
    call_args = mock_client.retrieve_and_generate.call_args[1]
    prompt_template = call_args["retrieveAndGenerateConfiguration"]["knowledgeBaseConfiguration"][
        "generationConfiguration"
    ]["promptTemplate"]["textPromptTemplate"]
    assert prompt_template == "Test prompt template"
    assert result["output"]["text"] == "response"


@patch("app.services.prompt_loader.load_prompt")
@patch("boto3.client")
def test_query_bedrock_check_config(mock_boto_client: Mock, mock_load_prompt: Mock, mock_env: Mock):
    """Test query_bedrock config loading"""
    # set up mocks
    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    mock_client.retrieve_and_generate.return_value = {"output": {"text": "response"}}
    mock_load_prompt.return_value = {
        "prompt_text": "Test prompt template",
        "inference_config": {"temperature": "0", "maxTokens": "1500", "topP": "1"},
    }

    # delete and import module to test
    if "app.services.bedrock" in sys.modules:
        del sys.modules["app.services.bedrock"]
    from app.services.bedrock import query_bedrock

    # perform operation
    query_bedrock("test query")

    # assertions
    call_args = mock_client.retrieve_and_generate.call_args[1]
    prompt_config = call_args["retrieveAndGenerateConfiguration"]["knowledgeBaseConfiguration"][
        "generationConfiguration"
    ]["inferenceConfig"]["textInferenceConfig"]

    assert prompt_config["temperature"] == "0"
    assert prompt_config["maxTokens"] == "1500"
    assert prompt_config["topP"] == "1"
