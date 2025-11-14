"""shared ai processor - validates query reformulation and bedrock integration"""

import pytest
from unittest.mock import patch
from app.services.ai_processor import process_ai_query


class TestAIProcessor:

    @patch("app.services.ai_processor.query_bedrock")
    @patch("app.services.ai_processor.reformulate_query")
    def test_process_ai_query_without_session(self, mock_reformulate, mock_bedrock):
        """new conversation: no session context passed to bedrock"""
        mock_reformulate.return_value = "reformulated: How to authenticate EPS API?"
        mock_bedrock.return_value = {
            "output": {"text": "To authenticate with EPS API, you need..."},
            "sessionId": "new-session-abc123",
            "citations": [{"title": "EPS Authentication Guide", "uri": "https://example.com/auth"}],
        }

        result = process_ai_query("How to authenticate EPS API?")

        assert result["text"] == "To authenticate with EPS API, you need..."
        assert result["session_id"] == "new-session-abc123"
        assert len(result["citations"]) == 1
        assert result["citations"][0]["title"] == "EPS Authentication Guide"
        assert "kb_response" in result

        mock_reformulate.assert_called_once_with("How to authenticate EPS API?")
        mock_bedrock.assert_called_once_with("reformulated: How to authenticate EPS API?", None)

    @patch("app.services.ai_processor.query_bedrock")
    @patch("app.services.ai_processor.reformulate_query")
    def test_process_ai_query_with_session(self, mock_reformulate, mock_bedrock):
        """conversation continuity: existing session maintained across queries"""
        mock_reformulate.return_value = "reformulated: What about rate limits?"
        mock_bedrock.return_value = {
            "output": {"text": "EPS API has rate limits of..."},
            "sessionId": "existing-session-456",
            "citations": [],
        }

        result = process_ai_query("What about rate limits?", session_id="existing-session-456")

        assert result["text"] == "EPS API has rate limits of..."
        assert result["session_id"] == "existing-session-456"
        assert result["citations"] == []
        assert "kb_response" in result

        mock_reformulate.assert_called_once_with("What about rate limits?")
        mock_bedrock.assert_called_once_with("reformulated: What about rate limits?", "existing-session-456")

    @patch("app.services.ai_processor.query_bedrock")
    @patch("app.services.ai_processor.reformulate_query")
    def test_process_ai_query_reformulate_error(self, mock_reformulate, mock_bedrock):
        """graceful degradation: reformulation failure bubbles up"""
        mock_reformulate.side_effect = Exception("Query reformulation failed")

        with pytest.raises(Exception) as exc_info:
            process_ai_query("How to authenticate EPS API?")

        assert "Query reformulation failed" in str(exc_info.value)
        mock_bedrock.assert_not_called()

    @patch("app.services.ai_processor.query_bedrock")
    @patch("app.services.ai_processor.reformulate_query")
    def test_process_ai_query_bedrock_error(self, mock_reformulate, mock_bedrock):
        """bedrock service failure: error propagated to caller"""
        mock_reformulate.return_value = "reformulated query"
        mock_bedrock.side_effect = Exception("Bedrock service error")

        with pytest.raises(Exception) as exc_info:
            process_ai_query("How to authenticate EPS API?")

        assert "Bedrock service error" in str(exc_info.value)
        mock_reformulate.assert_called_once()

    @patch("app.services.ai_processor.query_bedrock")
    @patch("app.services.ai_processor.reformulate_query")
    def test_process_ai_query_missing_citations(self, mock_reformulate, mock_bedrock):
        """bedrock response incomplete: citations default to empty list"""
        mock_reformulate.return_value = "reformulated query"
        mock_bedrock.return_value = {
            "output": {"text": "Response without citations"},
            "sessionId": "session-123",
            # No citations key
        }

        result = process_ai_query("test query")

        assert result["text"] == "Response without citations"
        assert result["session_id"] == "session-123"
        assert result["citations"] == []  # safe default when bedrock omits citations

    @patch("app.services.ai_processor.query_bedrock")
    @patch("app.services.ai_processor.reformulate_query")
    def test_process_ai_query_missing_session_id(self, mock_reformulate, mock_bedrock):
        """bedrock response incomplete: session_id properly handles None"""
        mock_reformulate.return_value = "reformulated query"
        mock_bedrock.return_value = {
            "output": {"text": "Response without session"},
            "citations": [],
            # No sessionId key
        }

        result = process_ai_query("test query")

        assert result["text"] == "Response without session"
        assert result["session_id"] is None  # explicit None when bedrock omits sessionId
        assert result["citations"] == []

    @patch("app.services.ai_processor.query_bedrock")
    @patch("app.services.ai_processor.reformulate_query")
    def test_process_ai_query_empty_query(self, mock_reformulate, mock_bedrock):
        """edge case: empty query still processed through full pipeline"""
        mock_reformulate.return_value = ""
        mock_bedrock.return_value = {
            "output": {"text": "Please provide a question"},
            "sessionId": "session-empty",
            "citations": [],
        }

        result = process_ai_query("")

        assert result["text"] == "Please provide a question"
        mock_reformulate.assert_called_once_with("")
        mock_bedrock.assert_called_once_with("", None)

    @patch("app.services.ai_processor.query_bedrock")
    @patch("app.services.ai_processor.reformulate_query")
    def test_process_ai_query_includes_raw_response(self, mock_reformulate, mock_bedrock):
        """slack needs raw bedrock data: kb_response preserved for session handling"""
        mock_reformulate.return_value = "reformulated query"
        raw_response = {
            "output": {"text": "Test response"},
            "sessionId": "test-123",
            "citations": [{"title": "Test", "uri": "test.com"}],
            "metadata": {"some": "extra_data"},
        }
        mock_bedrock.return_value = raw_response

        result = process_ai_query("test query")

        assert result["kb_response"] == raw_response
        assert result["kb_response"]["metadata"]["some"] == "extra_data"
