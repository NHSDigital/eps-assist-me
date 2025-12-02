import sys
import pytest
from unittest.mock import ANY, Mock, patch, MagicMock
from botocore.exceptions import ClientError


@pytest.fixture
def mock_logger():
    return MagicMock()


@patch("app.services.prompt_loader.load_prompt")
@patch("app.services.bedrock.invoke_model")
def test_reformulate_query_returns_string(mock_invoke_model: Mock, mock_load_prompt: Mock, mock_env: Mock):
    """Test that reformulate_query returns a string without crashing"""
    # set up mocks
    mock_load_prompt.return_value = {"prompt_text": "Test reformat. {{user_query}}", "inference_config": {}}
    mock_invoke_model.return_value = {"content": [{"text": "foo"}]}

    # delete and import module to test
    if "app.services.query_reformulator" in sys.modules:
        del sys.modules["app.services.query_reformulator"]
    from app.services.query_reformulator import reformulate_query

    # perform operation
    result = reformulate_query("How do I use EPS?")

    # assertions
    # Function should return a string (either reformulated or fallback to original)
    assert isinstance(result, str)
    assert len(result) > 0
    assert result == "foo"
    mock_load_prompt.assert_called_once_with("test-prompt", "DRAFT")
    mock_invoke_model.assert_called_once_with(
        prompt="Test reformat. How do I use EPS?", model_id="test-model", client=ANY, inference_config={}
    )


@patch("app.services.prompt_loader.load_prompt")
def test_reformulate_query_prompt_load_error(mock_load_prompt: Mock, mock_env: Mock):
    # set up mocks
    mock_load_prompt.side_effect = Exception("Prompt not found")

    # delete and import module to test
    if "app.services.query_reformulator" in sys.modules:
        del sys.modules["app.services.query_reformulator"]
    from app.services.query_reformulator import reformulate_query

    # perform operation
    original_query = "How do I use EPS?"
    result = reformulate_query(original_query)

    # assertions
    assert result == original_query


@patch("app.services.prompt_loader.load_prompt")
@patch("app.services.bedrock.invoke_model")
def test_reformulate_query_bedrock_error(mock_invoke_model: Mock, mock_load_prompt: Mock, mock_env: Mock):
    """Test query reformulation with Bedrock API error"""
    # set up mocks
    mock_load_prompt.return_value = "Reformulate this query: {{user_query}}"
    mock_invoke_model.side_effect = ClientError({"Error": {"Code": "ThrottlingException"}}, "InvokeModel")

    # delete and import module to test
    if "app.services.query_reformulator" in sys.modules:
        del sys.modules["app.services.query_reformulator"]
    from app.services.query_reformulator import reformulate_query

    # perform operation
    result = reformulate_query("original query")

    # assertions
    assert result == "original query"


@patch("app.services.prompt_loader.load_prompt")
@patch("app.services.bedrock.invoke_model")
def test_reformulate_query_bedrock_invoke_model(mock_invoke_model: Mock, mock_load_prompt: Mock, mock_env: Mock):
    """Test query reformulation with successful Bedrock invoke_model call"""
    # set up mocks
    mock_load_prompt.return_value = {"prompt_text": "Reformulate this query: {{user_query}}"}
    mock_invoke_model.return_value = {"content": [{"text": "reformulated query"}]}

    # delete and import module to test
    if "app.services.query_reformulator" in sys.modules:
        del sys.modules["app.services.query_reformulator"]
    from app.services.query_reformulator import reformulate_query

    # perform operation
    result = reformulate_query("original query")

    # assertions
    assert result == "reformulated query"
