"""direct lambda invocation - validates bypassing slack infrastructure entirely"""

from unittest.mock import Mock, patch
from app.handler import handle_direct_invocation


class TestDirectInvocation:

    @patch("app.services.ai_processor.process_ai_query")
    def test_successful_direct_invocation_without_session(self, mock_process_ai_query):
        """new conversation: no session context from previous queries"""
        mock_process_ai_query.return_value = {
            "text": "AI response about EPS API authentication",
            "session_id": "new-session-123",
            "citations": [{"title": "EPS API Guide", "uri": "https://example.com"}],
            "kb_response": {"sessionId": "new-session-123"},
        }

        event = {"invocation_type": "direct", "query": "How do I authenticate with EPS API?"}

        result = handle_direct_invocation(event, Mock())

        assert result["statusCode"] == 200
        assert result["response"]["text"] == "AI response about EPS API authentication"
        assert result["response"]["session_id"] == "new-session-123"
        assert len(result["response"]["citations"]) == 1
        assert "timestamp" in result["response"]

        mock_process_ai_query.assert_called_once_with("How do I authenticate with EPS API?", None)

    @patch("app.services.ai_processor.process_ai_query")
    def test_successful_direct_invocation_with_session(self, mock_process_ai_query):
        """conversation continuity: session maintained across direct calls"""
        mock_process_ai_query.return_value = {
            "text": "Follow-up response",
            "session_id": "existing-session-456",
            "citations": [],
            "kb_response": {"sessionId": "existing-session-456"},
        }

        event = {"invocation_type": "direct", "query": "What about rate limits?", "session_id": "existing-session-456"}

        result = handle_direct_invocation(event, Mock())

        assert result["statusCode"] == 200
        assert result["response"]["text"] == "Follow-up response"
        assert result["response"]["session_id"] == "existing-session-456"
        assert result["response"]["citations"] == []
        assert "timestamp" in result["response"]

        mock_process_ai_query.assert_called_once_with("What about rate limits?", "existing-session-456")

    def test_direct_invocation_missing_query(self):
        """input validation: query field required for processing"""
        event = {"invocation_type": "direct"}

        result = handle_direct_invocation(event, Mock())

        assert result["statusCode"] == 400
        assert "Missing required field: query" in result["response"]["error"]
        assert "timestamp" in result["response"]

    def test_direct_invocation_empty_query(self):
        """edge case: empty string treated same as missing query"""
        event = {"invocation_type": "direct", "query": ""}

        result = handle_direct_invocation(event, Mock())

        assert result["statusCode"] == 400
        assert "Missing required field: query" in result["response"]["error"]
        assert "timestamp" in result["response"]

    @patch("app.services.ai_processor.process_ai_query")
    def test_direct_invocation_processing_error(self, mock_process_ai_query):
        """ai service failure: graceful error response to caller"""
        mock_process_ai_query.side_effect = Exception("Bedrock service unavailable")

        event = {"invocation_type": "direct", "query": "How do I authenticate with EPS API?"}

        result = handle_direct_invocation(event, Mock())

        assert result["statusCode"] == 500
        assert result["response"]["error"] == "Internal server error"
        assert "timestamp" in result["response"]

    @patch("app.services.ai_processor.process_ai_query")
    def test_direct_invocation_with_none_query(self, mock_process_ai_query):
        """edge case: None query handled same as empty string"""
        event = {"invocation_type": "direct", "query": None}

        result = handle_direct_invocation(event, Mock())

        assert result["statusCode"] == 400
        assert "Missing required field: query" in result["response"]["error"]

    @patch("app.services.ai_processor.process_ai_query")
    def test_direct_invocation_whitespace_query(self, mock_process_ai_query):
        """input sanitization: whitespace-only queries rejected"""
        event = {"invocation_type": "direct", "query": "   \n\t   "}

        result = handle_direct_invocation(event, Mock())

        assert result["statusCode"] == 400
        assert "Missing required field: query" in result["response"]["error"]

    @patch("app.services.ai_processor.process_ai_query")
    def test_direct_invocation_response_structure(self, mock_process_ai_query):
        """api contract: response structure matches expected format"""
        mock_process_ai_query.return_value = {
            "text": "Test response",
            "session_id": "test-session",
            "citations": [
                {"title": "Doc 1", "uri": "https://example.com/1"},
                {"title": "Doc 2", "uri": "https://example.com/2"},
            ],
            "kb_response": {"sessionId": "test-session"},
        }

        event = {"invocation_type": "direct", "query": "Test query"}

        result = handle_direct_invocation(event, Mock())

        # api contract validation: all required fields present
        assert "statusCode" in result
        assert "response" in result
        assert "text" in result["response"]
        assert "session_id" in result["response"]
        assert "citations" in result["response"]
        assert "timestamp" in result["response"]

        # citation passthrough: bedrock data structure preserved
        assert len(result["response"]["citations"]) == 2
        assert result["response"]["citations"][0]["title"] == "Doc 1"
        assert result["response"]["citations"][1]["uri"] == "https://example.com/2"

    @patch("app.services.ai_processor.process_ai_query")
    def test_direct_invocation_timestamp_format(self, mock_process_ai_query):
        """timestamp format: iso8601 with Z suffix for consistency"""
        mock_process_ai_query.return_value = {
            "text": "Test response",
            "session_id": None,
            "citations": [],
            "kb_response": {},
        }

        event = {"invocation_type": "direct", "query": "Test query"}

        result = handle_direct_invocation(event, Mock())

        timestamp = result["response"]["timestamp"]
        # iso8601 validation: parseable datetime with utc marker
        assert timestamp.endswith("Z")
        assert "T" in timestamp
        # format verification: datetime parsing confirms structure
        from datetime import datetime

        datetime.fromisoformat(timestamp.rstrip("Z"))
