import pytest
from unittest.mock import patch
from app.services.prompt_loader import load_prompt


def test_load_prompt_function_exists():
    """Test that the load_prompt function exists and is callable"""
    assert callable(load_prompt)


def test_load_prompt_requires_prompt_name():
    """Test that load_prompt requires a prompt name parameter"""
    with pytest.raises(TypeError):
        load_prompt()  # Should fail without prompt_name


def test_load_prompt_handles_missing_environment():
    """Test that load_prompt handles missing AWS_REGION environment variable"""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(Exception):
            load_prompt("test-prompt")
