import json
import pytest

from unittest.mock import MagicMock, Mock, patch
import os


TEST_BOT_TOKEN = "test-bot-token"
TEST_SIGNING_SECRET = "test-signing-secret"


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
        "QUERY_REFORMULATION_MODEL_ID": "test-model",
        "QUERY_REFORMULATION_PROMPT_NAME": "test-prompt",
        "QUERY_REFORMULATION_PROMPT_VERSION": "DRAFT",
        "RAG_RESPONSE_PROMPT_NAME": "test-rag-prompt",
        "RAG_RESPONSE_PROMPT_VERSION": "DRAFT",
    }
    env_vars["AWS_DEFAULT_REGION"] = env_vars["AWS_REGION"]
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def lambda_context():
    """Mock Lambda context"""
    context = Mock()
    context.function_name = "test-function"
    context.aws_request_id = "test-request-id"
    return context


@pytest.fixture
def mock_get_parameter():
    def fake_get_parameter(name: str, *args, **kwargs):
        return {
            "/test/bot-token": json.dumps({"token": "test-token"}),
            "/test/signing-secret": json.dumps({"secret": "test-secret"}),
        }[name]

    with patch("app.core.config.get_parameter", side_effect=fake_get_parameter) as mock:
        yield mock


@pytest.fixture
def mock_slack_app():
    with patch("slack_bolt.App") as mock_app_cls:
        mock_instance = MagicMock()
        mock_app_cls.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_table():
    with patch("app.core.config.get_slack_bot_state_table") as mock_func:
        fake_table = MagicMock()
        mock_func.return_value = fake_table
        yield fake_table
