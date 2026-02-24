"""
shared AI processing service - extracted to avoid duplication

both slack handlers and direct invocation use identical logic for query
reformulation and bedrock interaction. single source of truth for AI flows.
"""

from app.services.bedrock import query_bedrock
from app.core.config import get_retrieve_generate_config, get_logger
from app.core.types import AIProcessorResponse
from app.services.prompt_loader import load_prompt

logger = get_logger()


def process_ai_query(user_query: str, session_id: str | None = None) -> AIProcessorResponse:
    """shared AI processing logic for both slack and direct invocation"""
    # session_id enables conversation continuity across multiple queries
    config = get_retrieve_generate_config()

    reformulation_prompt_template = load_prompt(
        config.REFORMULATION_PROMPT_NAME,
        config.REFORMULATION_PROMPT_VERSION,
    )
    # Don't provide sessionId as this conflicts with the sessions knowledgebase settings
    reformulation_prompt = query_bedrock(user_query, reformulation_prompt_template, config)
    reformulation_text = reformulation_prompt["output"]["text"]

    logger.debug("reformulation_text", extra={"text": reformulation_text})

    rag_prompt_template = load_prompt(config.RAG_RESPONSE_PROMPT_NAME, config.RAG_RESPONSE_PROMPT_VERSION)
    kb_response = query_bedrock(
        user_query=reformulation_text,
        prompt_template=rag_prompt_template,
        config=config,
        session_id=session_id,
        rerank_results=True,
    )

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
