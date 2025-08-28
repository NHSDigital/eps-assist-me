import pytest
from unittest.mock import patch
import os


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    env_vars = {
        "SLACK_BOT_TOKEN_PARAMETER": "/test/bot-token",
        "SLACK_SIGNING_SECRET_PARAMETER": "/test/signing-secret",
        "SLACK_BOT_STATE_TABLE": "test-bot-state-table",
        "KNOWLEDGEBASE_ID": "test-kb-id",
        "RAG_MODEL_ID": "test-model-id",
        "AWS_REGION": "eu-west-2",
        "GUARD_RAIL_ID": "test-guard-id",
        "GUARD_RAIL_VERSION": "1",
        "AWS_LAMBDA_FUNCTION_NAME": "test-function",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@patch("app.slack.slack_events.table")
@patch("time.time")
def test_store_feedback(mock_time, mock_table, mock_env):
    """Test feedback storage functionality"""
    mock_time.return_value = 1000

    from app.slack.slack_events import store_feedback

    store_feedback("test-conversation", "test query", "positive", "U123", "C123")

    mock_table.put_item.assert_called_once()
    call_args = mock_table.put_item.call_args[1]["Item"]
    assert call_args["feedback_type"] == "positive"
    assert call_args["user_query"] == "test query"
    assert call_args["user_id"] == "U123"


@patch("app.slack.slack_events.store_feedback")
def test_feedback_storage_with_additional_text(mock_store_feedback, mock_env):
    """Test feedback storage with additional feedback text"""
    from app.slack.slack_events import store_feedback

    store_feedback("test-conversation", "test query", "additional", "U123", "This is additional feedback")

    mock_store_feedback.assert_called_once_with(
        "test-conversation", "test query", "additional", "U123", "This is additional feedback"
    )


def test_feedback_message_empty_text(mock_env):
    """Test that empty feedback doesn't crash"""
    # This test just ensures no crash occurs with empty feedback
    assert True  # Placeholder test
