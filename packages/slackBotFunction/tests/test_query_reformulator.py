import pytest
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
