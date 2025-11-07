"""
shared AI processing service - extracted to avoid duplication

both slack handlers and direct invocation use identical logic for query
reformulation and bedrock interaction. single source of truth for AI flows.
"""

from typing import Dict, Any, Optional
from app.services.bedrock import query_bedrock
from app.services.query_reformulator import reformulate_query
from app.core.config import get_logger

logger = get_logger()


def process_ai_query(user_query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """shared AI processing logic for both slack and direct invocation"""
    # reformulate: improves vector search quality in knowledge base
    reformulated_query = reformulate_query(user_query)

    # session_id enables conversation continuity across multiple queries
    kb_response = query_bedrock(reformulated_query, session_id)

    return {
        "text": kb_response["output"]["text"],
        "session_id": kb_response.get("sessionId"),
        "citations": kb_response.get("citations", []),
        "kb_response": kb_response,  # slack needs raw bedrock data for session handling
    }
