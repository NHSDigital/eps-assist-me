import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from app.services.prompt_loader import load_prompt, get_prompt_id_from_name


@pytest.fixture
def mock_logger():
    return MagicMock()


@patch("app.services.prompt_loader.boto3.client")
@patch.dict("os.environ", {"AWS_REGION": "eu-west-2"})
def test_load_prompt_success_draft(mock_boto_client, mock_logger):
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    # Mock list_prompts to return prompt ID
    mock_client.list_prompts.return_value = {"promptSummaries": [{"name": "test-prompt", "id": "ABC1234567"}]}

    # Mock get_prompt for DRAFT version
    mock_client.get_prompt.return_value = {
        "variants": [{"templateConfiguration": {"text": {"text": "Test prompt"}}}],
        "version": "DRAFT",
    }

    result = load_prompt(mock_logger, "test-prompt")
    assert result == "Test prompt"
    mock_client.get_prompt.assert_called_once_with(promptIdentifier="ABC1234567")


@patch("app.services.prompt_loader.boto3.client")
@patch.dict("os.environ", {"AWS_REGION": "eu-west-2"})
def test_load_prompt_success_versioned(mock_boto_client, mock_logger):
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.list_prompts.return_value = {"promptSummaries": [{"name": "test-prompt", "id": "ABC1234567"}]}

    mock_client.get_prompt.return_value = {
        "variants": [{"templateConfiguration": {"text": {"text": "Versioned prompt"}}}],
        "version": "1",
    }

    result = load_prompt(mock_logger, "test-prompt", "1")
    assert result == "Versioned prompt"
    mock_client.get_prompt.assert_called_once_with(promptIdentifier="ABC1234567", promptVersion="1")


@patch("app.services.prompt_loader.boto3.client")
@patch.dict("os.environ", {"AWS_REGION": "eu-west-2"})
def test_load_prompt_not_found(mock_boto_client, mock_logger):
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.list_prompts.return_value = {"promptSummaries": []}

    with pytest.raises(Exception, match="Could not find prompt ID"):
        load_prompt(mock_logger, "nonexistent-prompt")


@patch("app.services.prompt_loader.boto3.client")
@patch.dict("os.environ", {"AWS_REGION": "eu-west-2"})
def test_load_prompt_client_error(mock_boto_client, mock_logger):
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.list_prompts.return_value = {"promptSummaries": [{"name": "test-prompt", "id": "ABC1234567"}]}

    error = ClientError({"Error": {"Code": "ValidationException", "Message": "Invalid prompt"}}, "GetPrompt")
    mock_client.get_prompt.side_effect = error

    with pytest.raises(Exception, match="ValidationException - Invalid prompt"):
        load_prompt(mock_logger, "test-prompt")


@patch("app.services.prompt_loader.boto3.client")
@patch.dict("os.environ", {"AWS_REGION": "eu-west-2"})
def test_get_prompt_id_from_name_success(mock_boto_client, mock_logger):
    mock_client = MagicMock()
    mock_client.list_prompts.return_value = {"promptSummaries": [{"name": "test-prompt", "id": "ABC1234567"}]}

    result = get_prompt_id_from_name(mock_logger, mock_client, "test-prompt")
    assert result == "ABC1234567"


@patch("app.services.prompt_loader.boto3.client")
@patch.dict("os.environ", {"AWS_REGION": "eu-west-2"})
def test_get_prompt_id_from_name_not_found(mock_boto_client, mock_logger):
    mock_client = MagicMock()
    mock_client.list_prompts.return_value = {"promptSummaries": []}

    result = get_prompt_id_from_name(mock_logger, mock_client, "nonexistent")
    assert result is None


@patch("app.services.prompt_loader.boto3.client")
@patch.dict("os.environ", {"AWS_REGION": "eu-west-2"})
def test_get_prompt_id_client_error(mock_boto_client, mock_logger):
    mock_client = MagicMock()
    error = ClientError({"Error": {"Code": "AccessDenied"}}, "ListPrompts")
    mock_client.list_prompts.side_effect = error

    result = get_prompt_id_from_name(mock_logger, mock_client, "test-prompt")
    assert result is None


def test_load_prompt_missing_environment(mock_logger):
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(Exception):
            load_prompt(mock_logger, "test-prompt")
