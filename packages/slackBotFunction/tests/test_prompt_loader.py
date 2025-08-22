import pytest
from unittest.mock import patch, MagicMock
from app.services.prompt_loader import load_prompt


@patch("app.services.prompt_loader.boto3.client")
@patch.dict("os.environ", {"AWS_REGION": "eu-west-2"})
def test_load_prompt_success(mock_boto_client):
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.get_prompt.return_value = {
        "variants": [{"templateConfiguration": {"text": {"text": "Test prompt template"}}}]
    }
    mock_client.list_prompts.return_value = {"promptSummaries": []}
    mock_client.get_caller_identity.return_value = {"Arn": "test-arn"}

    # Disable debug for clean testing
    load_prompt._debug_run = True

    result = load_prompt("query-reformulation")

    assert result == "Test prompt template"
    mock_client.get_prompt.assert_called_with(promptIdentifier="query-reformulation", promptVersion="$LATEST")


@patch("app.services.prompt_loader.boto3.client")
@patch.dict("os.environ", {"AWS_REGION": "eu-west-2"})
def test_load_prompt_with_version(mock_boto_client):
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.get_prompt.return_value = {
        "variants": [{"templateConfiguration": {"text": {"text": "Versioned prompt template"}}}]
    }

    # Disable debug for clean testing
    load_prompt._debug_run = True

    result = load_prompt("query-reformulation", "1")

    assert result == "Versioned prompt template"
    mock_client.get_prompt.assert_called_with(promptIdentifier="query-reformulation", promptVersion="1")


@patch("app.services.prompt_loader.boto3.client")
@patch.dict("os.environ", {"AWS_REGION": "eu-west-2"})
def test_load_prompt_bedrock_error(mock_boto_client):
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    mock_client.get_prompt.side_effect = Exception("Bedrock error")

    # Disable debug for clean testing
    load_prompt._debug_run = True

    with pytest.raises(Exception, match="Bedrock error"):
        load_prompt("query-reformulation")
