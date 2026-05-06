"""Tests for query reformulation logic and the skip_reformulation flag."""

import pytest
from unittest.mock import call, patch, ANY
from app.services.ai_processor import process_ai_query


@pytest.fixture
def mock_config_setup(mock_load_prompt, mock_config):
    """Setup common mock configurations"""
    mock_load_prompt.return_value = {"prompt_text": "test_prompt", "model_id": "model_id", "inference_config": {}}
    mock_config.get_retrieve_generate_config.return_value = {
        "REFORMULATION_PROMPT_NAME": "test",
        "REFORMULATION_PROMPT_VERSION": "test",
        "RAG_RESPONSE_PROMPT_NAME": "test",
        "RAG_RESPONSE_PROMPT_VERSION": "test",
    }
    return mock_load_prompt, mock_config


class TestReformulation:

    @patch("app.services.ai_processor.get_retrieve_generate_config")
    @patch("app.services.ai_processor.load_prompt")
    @patch("app.services.ai_processor.query_bedrock")
    def test_reformulation_applied_by_default(self, mock_bedrock, mock_load_prompt, mock_config):
        """Tests that query reformulation is applied by default (skip_reformulation=False)."""
        # Mocking two sequential calls: 1. Reformulation, 2. RAG Response
        mock_bedrock.side_effect = [
            {"output": {"text": "Reformulated AI query"}, "sessionId": None},
            {
                "output": {"text": "Final RAG response"},
                "sessionId": "session-abc123",
                "citations": [{"title": "EPS Guide", "uri": "https://example.com"}],
            },
        ]

        result = process_ai_query("Original query")

        assert result["text"] == "Final RAG response"
        assert result["session_id"] == "session-abc123"
        assert len(result["citations"]) == 1

        # Verify Bedrock and prompt loader were both called twice
        assert mock_bedrock.call_count == 2
        assert mock_load_prompt.call_count == 2

        # Verify the second call to Bedrock uses the output of the first call
        mock_bedrock.assert_has_calls(
            [
                call("Original query", mock_load_prompt.return_value, ANY),
                call("Reformulated AI query", mock_load_prompt.return_value, ANY, None),
            ]
        )

    @patch("app.services.ai_processor.get_retrieve_generate_config")
    @patch("app.services.ai_processor.load_prompt")
    @patch("app.services.ai_processor.query_bedrock")
    def test_skip_reformulation_flag_true(self, mock_bedrock, mock_load_prompt, mock_config):
        """Tests that reformulation is entirely bypassed when skip_reformulation=True."""
        mock_bedrock.return_value = {
            "output": {"text": "Direct RAG response"},
            "sessionId": "session-skip456",
            "citations": [],
        }

        result = process_ai_query("Original query", skip_reformulation=True)

        assert result["text"] == "Direct RAG response"

        # Verify Bedrock and prompt loader were only called ONCE
        assert mock_bedrock.call_count == 1
        assert mock_load_prompt.call_count == 1

        # Verify it uses the original query directly for the RAG generation
        mock_bedrock.assert_called_once_with("Original query", mock_load_prompt.return_value, ANY, None)

    @patch("app.services.ai_processor.get_retrieve_generate_config")
    @patch("app.services.ai_processor.load_prompt")
    @patch("app.services.ai_processor.query_bedrock")
    def test_skip_reformulation_flag_false_explicit(self, mock_bedrock, mock_load_prompt, mock_config):
        """Tests explicit skip_reformulation=False still triggers the reformulation pipeline."""
        mock_bedrock.side_effect = [
            {"output": {"text": "Better formulated query"}, "sessionId": None},
            {"output": {"text": "Final RAG response"}, "sessionId": "session-123", "citations": []},
        ]

        # Explicitly passing the flag as False
        process_ai_query("Original query", skip_reformulation=False)

        assert mock_bedrock.call_count == 2
        mock_bedrock.assert_has_calls(
            [
                call("Original query", mock_load_prompt.return_value, ANY),
                call("Better formulated query", mock_load_prompt.return_value, ANY, None),
            ]
        )

    @patch("app.services.ai_processor.get_retrieve_generate_config")
    @patch("app.services.ai_processor.load_prompt")
    @patch("app.services.ai_processor.query_bedrock")
    def test_reformulation_with_existing_session(self, mock_bedrock, mock_load_prompt, mock_config):
        """Tests reformulation interacts properly when an active session_id is provided."""
        mock_session_id = "existing-session-789"
        mock_bedrock.side_effect = [
            {"output": {"text": "Reformulated query"}, "sessionId": None},
            {"output": {"text": "Follow-up RAG response"}, "sessionId": mock_session_id, "citations": []},
        ]

        result = process_ai_query("Follow-up query", session_id=mock_session_id)

        assert result["text"] == "Follow-up RAG response"
        assert result["session_id"] == mock_session_id

        # Ensure session_id isn't passed to the reformulation call, but IS passed to the RAG call
        mock_bedrock.assert_has_calls(
            [
                call("Follow-up query", mock_load_prompt.return_value, ANY),
                call("Reformulated query", mock_load_prompt.return_value, ANY, mock_session_id),
            ]
        )
