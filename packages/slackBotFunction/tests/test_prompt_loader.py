import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError


@pytest.fixture
def mock_logger():
    return MagicMock()


@patch("boto3.client")
def test_load_prompt_success_draft(mock_boto_client: Mock, mock_env: Mock):
    # set up mocks
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    # Mock list_prompts to return prompt ID
    mock_client.list_prompts.return_value = {"promptSummaries": [{"name": "test-prompt", "id": "ABC1234567"}]}

    # Mock get_prompt for DRAFT version
    mock_client.get_prompt.return_value = {
        "variants": [{"templateConfiguration": {"text": {"text": "Test prompt"}}, "inferenceConfiguration": {}}],
        "version": "DRAFT",
    }

    # delete and import module to test
    if "app.services.prompt_loader" in sys.modules:
        del sys.modules["app.services.prompt_loader"]
    from app.services.prompt_loader import load_prompt

    # perform operation
    result = load_prompt("test-prompt")

    # assertions
    assert result.get("prompt_text") == "Test prompt"
    mock_client.get_prompt.assert_called_once_with(promptIdentifier="ABC1234567")


@patch("boto3.client")
def test_load_prompt_success_versioned(mock_boto_client: Mock, mock_env: Mock):
    # set up mocks
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.list_prompts.return_value = {"promptSummaries": [{"name": "test-prompt", "id": "ABC1234567"}]}

    mock_client.get_prompt.return_value = {
        "variants": [{"templateConfiguration": {"text": {"text": "Versioned prompt"}}, "inferenceConfiguration": {}}],
        "version": "1",
    }

    # delete and import module to test
    if "app.services.prompt_loader" in sys.modules:
        del sys.modules["app.services.prompt_loader"]
    from app.services.prompt_loader import load_prompt

    # perform operation
    result = load_prompt("test-prompt", "1")

    # assertions
    assert result.get("prompt_text") == "Versioned prompt"
    mock_client.get_prompt.assert_called_once_with(promptIdentifier="ABC1234567", promptVersion="1")


@patch("boto3.client")
def test_load_prompt_not_found(mock_boto_client: Mock, mock_env: Mock):
    # set up mocks
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.list_prompts.return_value = {"promptSummaries": []}

    # delete and import module to test
    if "app.services.prompt_loader" in sys.modules:
        del sys.modules["app.services.prompt_loader"]
    from app.services.prompt_loader import load_prompt

    # perform operation
    with pytest.raises(Exception, match="Could not find prompt ID"):
        load_prompt("nonexistent-prompt")


@patch("boto3.client")
def test_load_prompt_client_error(mock_boto_client: Mock, mock_env: Mock):
    # set up mocks
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_client.list_prompts.return_value = {"promptSummaries": [{"name": "test-prompt", "id": "ABC1234567"}]}

    error = ClientError({"Error": {"Code": "ValidationException", "Message": "Invalid prompt"}}, "GetPrompt")
    mock_client.get_prompt.side_effect = error

    # delete and import module to test
    if "app.services.prompt_loader" in sys.modules:
        del sys.modules["app.services.prompt_loader"]
    from app.services.prompt_loader import load_prompt

    # perform operation

    with pytest.raises(Exception, match="ValidationException - Invalid prompt"):
        load_prompt("test-prompt")


def test_get_prompt_id_from_name_success(mock_env: Mock):
    # set up mocks
    mock_client = MagicMock()
    mock_client.list_prompts.return_value = {"promptSummaries": [{"name": "test-prompt", "id": "ABC1234567"}]}

    # delete and import module to test
    if "app.services.prompt_loader" in sys.modules:
        del sys.modules["app.services.prompt_loader"]
    from app.services.prompt_loader import get_prompt_id_from_name

    # perform operation
    result = get_prompt_id_from_name(mock_client, "test-prompt")

    # assertions
    assert result == "ABC1234567"


def test_get_prompt_id_from_name_not_found(mock_env: Mock):
    # set up mocks
    mock_client = MagicMock()
    mock_client.list_prompts.return_value = {"promptSummaries": []}

    # delete and import module to test
    if "app.services.prompt_loader" in sys.modules:
        del sys.modules["app.services.prompt_loader"]
    from app.services.prompt_loader import get_prompt_id_from_name

    # perform operation
    result = get_prompt_id_from_name(mock_client, "nonexistent")

    # assertions
    assert result is None


def test_get_prompt_id_client_error(mock_logger: Mock, mock_env: Mock):
    # set up mocks
    mock_client = MagicMock()
    error = ClientError({"Error": {"Code": "AccessDenied"}}, "ListPrompts")
    mock_client.list_prompts.side_effect = error

    # delete and import module to test
    if "app.services.prompt_loader" in sys.modules:
        del sys.modules["app.services.prompt_loader"]
    from app.services.prompt_loader import get_prompt_id_from_name

    result = get_prompt_id_from_name(mock_client, "test-prompt")

    # assertions
    assert result is None


def test_get_render_prompt_chat_dict(mock_logger: Mock, mock_env: Mock):
    # delete and import module to test
    if "app.services.prompt_loader" in sys.modules:
        del sys.modules["app.services.prompt_loader"]
    from app.services.prompt_loader import _render_prompt

    result = _render_prompt(
        {
            "chat": {
                "system": [
                    {"text": "Assistant prompt here."},
                ],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": "User prompt here."},
                        ],
                    },
                ],
            }
        },
    )

    # assertions
    assert result == "Assistant prompt here.\n\nHuman: User prompt here."


def test_get_render_prompt_chat_dict_multiple_questions(mock_logger: Mock, mock_env: Mock):
    # delete and import module to test
    if "app.services.prompt_loader" in sys.modules:
        del sys.modules["app.services.prompt_loader"]
    from app.services.prompt_loader import _render_prompt

    result = _render_prompt(
        {
            "chat": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": "First Prompt."},
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {"text": "Second Prompt."},
                        ],
                    },
                ],
            }
        },
    )

    # assertions
    assert result == "Human: First Prompt.\n\nHuman: Second Prompt."


def test_get_render_prompt_text_dict(mock_logger: Mock, mock_env: Mock):
    # delete and import module to test
    if "app.services.prompt_loader" in sys.modules:
        del sys.modules["app.services.prompt_loader"]
    from app.services.prompt_loader import _render_prompt

    result = _render_prompt(
        {
            "text": "Second Prompt.",
        },
    )

    # assertions
    assert result == "Second Prompt."


def test_render_prompt_raises_configuration_error_empty(mock_logger):
    with patch("app.core.config.get_logger", return_value=mock_logger):
        if "app.services.prompt_loader" in sys.modules:
            del sys.modules["app.services.prompt_loader"]
        from app.services.prompt_loader import _render_prompt
        from app.services.exceptions import PromptLoadError

        with pytest.raises(PromptLoadError) as excinfo:
            _render_prompt({})

        # Verify the exception and logger call
        assert excinfo.type is PromptLoadError
        assert str(excinfo.value) == "Unsupported prompt configuration. Keys: []"
        mock_logger.error.assert_called_once()


def test_render_prompt_raises_configuration_error_text_missing(mock_logger):
    with patch("app.core.config.get_logger", return_value=mock_logger):
        if "app.services.prompt_loader" in sys.modules:
            del sys.modules["app.services.prompt_loader"]
        from app.services.prompt_loader import _render_prompt
        from app.services.exceptions import PromptLoadError

        with pytest.raises(PromptLoadError) as excinfo:
            _render_prompt({"text": {}})

        # Verify the exception and logger call
        assert excinfo.type is PromptLoadError
        assert str(excinfo.value) == "Unsupported prompt configuration. Keys: ['text']"
        mock_logger.error.assert_called_once()
