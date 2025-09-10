import pytest
import json
from unittest.mock import patch, MagicMock
from app.services.query_reformulator import reformulate_query


@pytest.fixture
def mock_logger():
    return MagicMock()


def test_reformulate_query_returns_string(mock_logger):
    """Test that reformulate_query returns a string without crashing"""
    with patch.dict(
        "os.environ",
        {
            "AWS_REGION": "eu-west-2",
            "QUERY_REFORMULATION_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
            "QUERY_REFORMULATION_PROMPT_NAME": "query-reformulation",
        },
    ):
        result = reformulate_query(mock_logger, "How do I use EPS?")
        # Function should return a string (either reformulated or fallback to original)
        assert isinstance(result, str)
        assert len(result) > 0


def test_reformulate_query_prompt_load_error(mock_logger):
    with patch("app.services.query_reformulator.load_prompt") as mock_load_prompt, patch.dict(
        "os.environ",
        {
            "AWS_REGION": "eu-west-2",
            "QUERY_REFORMULATION_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
            "QUERY_REFORMULATION_PROMPT_NAME": "query-reformulation",
        },
    ):
        mock_load_prompt.side_effect = Exception("Prompt not found")

        original_query = "How do I use EPS?"
        result = reformulate_query(mock_logger, original_query)
        assert result == original_query


def test_reformulate_query_missing_prompt_name(mock_logger):
    with patch.dict(
        "os.environ",
        {"AWS_REGION": "eu-west-2", "QUERY_REFORMULATION_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0"},
    ):
        original_query = "test query"
        result = reformulate_query(mock_logger, original_query)
        assert result == original_query


@patch("app.services.query_reformulator.boto3.client")
@patch("app.services.query_reformulator.load_prompt")
def test_reformulate_query_success(mock_load_prompt, mock_boto_client, mock_logger):
    """Test successful query reformulation"""
    mock_load_prompt.return_value = "Reformulate this query: {{user_query}}"

    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    mock_client.invoke_model.return_value = {
        "body": MagicMock(read=lambda: json.dumps({"content": [{"text": "reformulated query"}]}).encode())
    }

    with patch.dict(
        "os.environ",
        {
            "AWS_REGION": "eu-west-2",
            "QUERY_REFORMULATION_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
            "QUERY_REFORMULATION_PROMPT_NAME": "test-prompt",
            "QUERY_REFORMULATION_PROMPT_VERSION": "1",
        },
    ):
        result = reformulate_query(mock_logger, "original query")
        assert result == "reformulated query"
        mock_load_prompt.assert_called_once_with(mock_logger, "test-prompt", "1")


@patch("app.services.query_reformulator.boto3.client")
@patch("app.services.query_reformulator.load_prompt")
def test_reformulate_query_bedrock_error(mock_load_prompt, mock_boto_client, mock_logger):
    """Test query reformulation with Bedrock API error"""
    from botocore.exceptions import ClientError

    mock_load_prompt.return_value = "Reformulate this query: {{user_query}}"
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    mock_client.invoke_model.side_effect = ClientError({"Error": {"Code": "ThrottlingException"}}, "InvokeModel")

    with patch.dict(
        "os.environ",
        {
            "AWS_REGION": "eu-west-2",
            "QUERY_REFORMULATION_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
            "QUERY_REFORMULATION_PROMPT_NAME": "test-prompt",
        },
    ):
        result = reformulate_query(mock_logger, "original query")
        assert result == "original query"


@patch("app.services.query_reformulator.load_prompt")
def test_reformulate_query_configuration_error(mock_load_prompt, mock_logger):
    """Test query reformulation with configuration error"""
    from app.services.exceptions import ConfigurationError

    mock_load_prompt.side_effect = ConfigurationError("Config error")

    with patch.dict(
        "os.environ",
        {
            "AWS_REGION": "eu-west-2",
            "QUERY_REFORMULATION_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
            "QUERY_REFORMULATION_PROMPT_NAME": "test-prompt",
        },
    ):
        result = reformulate_query(mock_logger, "original query")
        assert result == "original query"
