"""Pytest conftest for the RAG evaluation suite.

Provides xdist-safe bootstrap (resolves AWS resources once across all workers
via a file lock) and the judge_model fixture.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from filelock import FileLock

from evaluation.bedrock_judge import BedrockJudgeModel
from evaluation.chatbot import bootstrap


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "smoke: subset of tests forming the fast PR gate (~3 cases, 2 metrics)",
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    """Resolve Lambda name and KB ID once before any tests run.

    Uses a file lock so only the first xdist worker calls CloudFormation;
    the rest read cached values from a shared JSON file.
    """
    if not os.environ.get("CHATBOT_STACK_NAME"):
        return

    # Use a stable path so all workers (separate processes) share it.
    cache_file = Path(tempfile.gettempdir()) / "eval_bootstrap_cache.json"
    lock_file = Path(tempfile.gettempdir()) / "eval_bootstrap_cache.json.lock"

    with FileLock(str(lock_file)):
        if cache_file.is_file():
            data = json.loads(cache_file.read_text())
            os.environ["_EVAL_LAMBDA_NAME"] = data["lambda_name"]
            os.environ["_EVAL_KB_ID"] = data["kb_id"]
        else:
            bootstrap()
            cache_file.write_text(
                json.dumps(
                    {
                        "lambda_name": os.environ["_EVAL_LAMBDA_NAME"],
                        "kb_id": os.environ["_EVAL_KB_ID"],
                    }
                )
            )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    cache_file = Path(tempfile.gettempdir()) / "eval_bootstrap_cache.json"
    cache_file.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def judge_model() -> BedrockJudgeModel:
    return BedrockJudgeModel()
