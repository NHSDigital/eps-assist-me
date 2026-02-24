# """shared ai processor - validates query reformulation and bedrock integration"""

# import pytest
# from unittest.mock import call, patch, ANY
# from app.services.ai_processor import process_ai_query


# @pytest.fixture
# def mock_config_setup(mock_load_prompt, mock_config):
#     """Setup common mock configurations"""
#     mock_load_prompt.return_value = {"prompt_text": "test_prompt", "model_id": "model_id", "inference_config": {}}
#     mock_config.get_retrieve_generate_config.return_value = {
#         "REFORMULATION_PROMPT_NAME": "test",
#         "REFORMULATION_PROMPT_VERSION": "test",
#         "RAG_RESPONSE_PROMPT_NAME": "test",
#         "RAG_RESPONSE_PROMPT_VERSION": "test",
#     }
#     return mock_load_prompt, mock_config


# class TestAIProcessor:

#     @patch("app.services.ai_processor.get_retrieve_generate_config")
#     @patch("app.services.ai_processor.load_prompt")
#     @patch("app.services.ai_processor.query_bedrock")
#     def test_process_ai_query_without_session(self, mock_bedrock, mock_load_prompt, mock_config):
#         """new conversation: no session context passed to bedrock"""
#         mock_bedrock.return_value = {
#             "output": {"text": "To authenticate with EPS API, you need..."},
#             "sessionId": "new-session-abc123",
#             "citations": [{"title": "EPS Authentication Guide", "uri": "https://example.com/auth"}],
#         }

#         result = process_ai_query("How to authenticate EPS API?")

#         assert result["text"] == "To authenticate with EPS API, you need..."
#         assert result["session_id"] == "new-session-abc123"
#         assert len(result["citations"]) == 1
#         assert result["citations"][0]["title"] == "EPS Authentication Guide"
#         assert "kb_response" in result

#         assert mock_bedrock.call_count == 2
#         assert mock_load_prompt.call_count == 2

#         mock_bedrock.assert_has_calls(
#             [
#                 call("How to authenticate EPS API?", mock_load_prompt.return_value, ANY),
#                 call("To authenticate with EPS API, you need...", mock_load_prompt.return_value, ANY, None),
#             ]
#         )

#     @patch("app.services.ai_processor.get_retrieve_generate_config")
#     @patch("app.services.ai_processor.load_prompt")
#     @patch("app.services.ai_processor.query_bedrock")
#     def test_process_ai_query_with_session(self, mock_bedrock, mock_load_prompt, mock_config):
#         """conversation continuity: existing session maintained across queries"""
#         mock_prompt = "What about rate limits?"
#         mock_session_id = "existing-session-456"
#         mock_bedrock.return_value = {
#             "output": {"text": "EPS API has rate limits of..."},
#             "sessionId": mock_session_id,
#             "citations": [],
#         }

#         result = process_ai_query(mock_prompt, session_id="existing-session-456")

#         assert result["text"] == "EPS API has rate limits of..."
#         assert result["session_id"] == "existing-session-456"
#         assert result["citations"] == []
#         assert "kb_response" in result

#         mock_bedrock.assert_has_calls(
#             [
#                 call("What about rate limits?", mock_load_prompt.return_value, ANY),
#                 call("EPS API has rate limits of...", mock_load_prompt.return_value, ANY, mock_session_id),
#             ]
#         )

#     @patch("app.services.ai_processor.get_retrieve_generate_config")
#     @patch("app.services.ai_processor.load_prompt")
#     @patch("app.services.ai_processor.query_bedrock")
#     def test_process_ai_query_bedrock_error(self, mock_bedrock, mock_load_prompt, mock_config):
#         """bedrock service failure: error propagated to caller"""
#         mock_bedrock.side_effect = Exception("Bedrock service error")
#         with pytest.raises(Exception) as exc_info:
#             process_ai_query("How to authenticate EPS API?")

#         assert "Bedrock service error" in str(exc_info.value)

#     @patch("app.services.ai_processor.get_retrieve_generate_config")
#     @patch("app.services.ai_processor.load_prompt")
#     @patch("app.services.ai_processor.query_bedrock")
#     def test_process_ai_query_missing_citations(self, mock_bedrock, mock_load_prompt, mock_config):
#         """bedrock response incomplete: citations default to empty list"""
#         mock_bedrock.return_value = {
#             "output": {"text": "Response without citations"},
#             "sessionId": "session-123",
#             # No citations key
#         }

#         result = process_ai_query("test query")

#         assert result["text"] == "Response without citations"
#         assert result["session_id"] == "session-123"
#         assert result["citations"] == []  # safe default when bedrock omits citations

#     @patch("app.services.ai_processor.get_retrieve_generate_config")
#     @patch("app.services.ai_processor.load_prompt")
#     @patch("app.services.ai_processor.query_bedrock")
#     def test_process_ai_query_missing_session_id(self, mock_bedrock, mock_load_prompt, mock_config):
#         """bedrock response incomplete: session_id properly handles None"""
#         mock_bedrock.return_value = {
#             "output": {"text": "Response without session"},
#             "citations": [],
#             # No sessionId key
#         }

#         result = process_ai_query("test query")

#         assert result["text"] == "Response without session"
#         assert result["session_id"] is None  # explicit None when bedrock omits sessionId
#         assert result["citations"] == []

#     @patch("app.services.ai_processor.get_retrieve_generate_config")
#     @patch("app.services.ai_processor.load_prompt")
#     @patch("app.services.ai_processor.query_bedrock")
#     def test_process_ai_query_empty_query(self, mock_bedrock, mock_load_prompt, mock_config):
#         """edge case: empty query still processed through full pipeline"""
#         mock_bedrock.return_value = {
#             "output": {"text": "Please provide a question"},
#             "sessionId": "session-empty",
#             "citations": [],
#         }

#         result = process_ai_query("")

#         assert result["text"] == "Please provide a question"
#         mock_bedrock.assert_called_with

#         mock_bedrock.assert_has_calls(
#             [
#                 call("", ANY, ANY),
#                 call("Please provide a question", ANY, ANY, None),
#             ]
#         )

#     @patch("app.services.ai_processor.get_retrieve_generate_config")
#     @patch("app.services.ai_processor.load_prompt")
#     @patch("app.services.ai_processor.query_bedrock")
#     def test_process_ai_query_includes_raw_response(self, mock_bedrock, mock_load_prompt, mock_config):
#         """slack needs raw bedrock data: kb_response preserved for session handling"""
#         raw_response = {
#             "output": {"text": "Test response"},
#             "sessionId": "test-123",
#             "citations": [{"title": "Test", "uri": "test.com"}],
#             "metadata": {"some": "extra_data"},
#         }
#         mock_bedrock.return_value = raw_response

#         result = process_ai_query("test query")

#         assert result["kb_response"] == raw_response
#         assert result["kb_response"]["metadata"]["some"] == "extra_data"
