"""
Shared fixtures for Ragas evaluation tests.
"""

import logging

import pytest

from evaluation.config import LAMBDA_FUNCTION_NAME

logger = logging.getLogger(__name__)


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "ragas: Ragas quality evaluation tests (require deployed infrastructure)")


@pytest.fixture(scope="session", autouse=True)
def check_environment():
    """Ensure required environment variables are set before running any ragas tests."""
    if not LAMBDA_FUNCTION_NAME:
        pytest.skip(
            "RAGAS_LAMBDA_FUNCTION_NAME not set — skipping Ragas evaluation. "
            "Set this environment variable to the deployed Lambda function name."
        )
