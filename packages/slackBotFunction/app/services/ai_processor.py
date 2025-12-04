"""
shared AI processing service - extracted to avoid duplication

both slack handlers and direct invocation use identical logic for query
reformulation and bedrock interaction. single source of truth for AI flows.
"""

from app.services.bedrock import query_bedrock
from app.services.query_reformulator import reformulate_query
from app.core.config import get_logger
from app.core.types import AIProcessorResponse

logger = get_logger()


async def process_ai_query(user_query: str, session_id: str | None = None) -> AIProcessorResponse:
    """shared AI processing logic for both slack and direct invocation"""
    # reformulate: improves vector search quality in knowledge base
    reformulated_query = reformulate_query(user_query)

    # session_id enables conversation continuity across multiple queries
    response_text = ""
    citations = []
    raw_response = []
    session_id_from_response = None

    # call bedrock function and get results
    bedrock_response = query_bedrock(reformulated_query, session_id)
    session_id_from_response = bedrock_response.get("sessionId")

    # iterate through bedrock stream events to build complete response
    async for event in bedrock_response["stream"]:
        logger.info(
            "[New] response from bedrock",
            extra={"session_id": session_id_from_response, "event": event},
        )

        raw_response.append(event)

        # extract generated text from output events
        if "output" in event:
            output_text = event["output"].get("text", "")
            response_text += output_text

        # extract citations from citation events
        if "citation" in event:
            citation_data = event["citation"]
            citations.extend(citation_data)

    logger.info(
        "[Complete] response from bedrock",
        extra={"session_id": session_id_from_response, "has_citations": len(citations) > 0, "citations": citations},
    )

    return {
        "text": response_text,
        "session_id": session_id_from_response,
        "citations": citations,
    }
