"""
shared AI processing service - extracted to avoid duplication

both slack handlers and direct invocation use identical logic for query
reformulation and bedrock interaction. single source of truth for AI flows.
"""

from app.services.bedrock import query_bedrock
from app.core.config import get_logger
from app.core.types import AIProcessorResponse

logger = get_logger()


def process_ai_query(user_query: str, session_id: str | None = None) -> AIProcessorResponse:
    """shared AI processing logic for both slack and direct invocation"""
    # session_id enables conversation continuity across multiple queries
    kb_response = query_bedrock(user_query, session_id)

    logger.info(
        "response from bedrock",
        extra={"response_text": kb_response},
    )

    return {
        "text": kb_response["output"]["text"],
        "session_id": kb_response.get("sessionId"),
        "citations": kb_response.get("citations", []),
        "kb_response": kb_response,  # slack needs raw bedrock data for session handling
    }
