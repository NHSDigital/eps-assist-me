import json
import pytest

from unittest.mock import MagicMock, Mock, patch
import os


TEST_BOT_TOKEN = "test-bot-token"


@pytest.fixture
def mock_env():
    """Mock environment variables"""
    env_vars = {
        "SLACK_BOT_TOKEN_PARAMETER": "/test/bot-token",
    }
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
            "/test/bot-token": json.dumps({"token": TEST_BOT_TOKEN}),
        }[name]

    with patch("app.core.config.get_parameter", side_effect=fake_get_parameter) as mock:
        yield mock


@pytest.fixture
def mock_web_client():
    with patch("slack_sdk.WebClient") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        yield mock_instance
