"""
Semantic caching for RAG responses using DynamoDB.

Caches query→response pairs keyed by a normalized hash of the user query.
Only first-turn queries (no session) are cached to avoid stale conversation context.
Cache entries have a configurable TTL to ensure freshness as the knowledge base evolves.
"""

import hashlib
import json
import traceback
from time import time
from typing import Any

from app.core.config import get_logger, get_slack_bot_state_table

logger = get_logger()

# Cache configuration
CACHE_TTL_SECONDS = 86400  # 24 hours — balances freshness with cost savings
CACHE_PREFIX = "cache#"


def _normalize_query(query: str) -> str:
    """Normalize query for consistent cache keys — lowercase, strip, collapse whitespace."""
    return " ".join(query.lower().strip().split())


def _hash_query(query: str) -> str:
    """Generate a short hash key from the normalized query."""
    normalized = _normalize_query(query)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def get_cached_response(query: str) -> dict[str, Any] | None:
    """
    Look up a cached RAG response for the given query.

    Returns:
        Cached response dict matching AIProcessorResponse shape, or None on miss/expiry.
    """
    try:
        query_hash = _hash_query(query)
        table = get_slack_bot_state_table()
        start = time()

        result = table.get_item(Key={"pk": f"{CACHE_PREFIX}{query_hash}", "sk": "response"})

        duration = time() - start
        item = result.get("Item")

        if not item:
            logger.info("Cache miss", extra={"query_hash": query_hash, "duration": duration})
            return None

        # Check TTL manually as DynamoDB TTL deletion is eventually consistent
        if item.get("ttl", 0) < time():
            logger.info("Cache expired", extra={"query_hash": query_hash})
            return None

        cached_data = json.loads(item["response_data"])
        logger.info(
            "Cache hit",
            extra={"query_hash": query_hash, "duration": duration},
        )
        return cached_data

    except Exception:
        # Cache failures should never break the main flow
        logger.warning("Cache lookup failed", extra={"error": traceback.format_exc()})
        return None


def store_cached_response(query: str, response_data: dict[str, Any]) -> None:
    """
    Store a RAG response in the cache.

    Only the serializable parts of the response are cached (text, session_id, citations).
    The raw kb_response is excluded as it contains non-serializable Bedrock metadata.

    Args:
        query: Original user query
        response_data: AIProcessorResponse dict to cache
    """
    try:
        query_hash = _hash_query(query)
        table = get_slack_bot_state_table()
        now = int(time())

        # Cache only the portable response fields — exclude kb_response (not needed for cache hits)
        cacheable_data = {
            "text": response_data["text"],
            "session_id": None,  # cached responses don't carry session state
            "citations": response_data.get("citations", []),
        }

        item = {
            "pk": f"{CACHE_PREFIX}{query_hash}",
            "sk": "response",
            "query_normalized": _normalize_query(query),
            "response_data": json.dumps(cacheable_data),
            "created_at": now,
            "ttl": now + CACHE_TTL_SECONDS,
        }

        table.put_item(Item=item)
        logger.info(
            "Cached response",
            extra={"query_hash": query_hash, "ttl_seconds": CACHE_TTL_SECONDS},
        )

    except Exception:
        # Cache failures should never break the main flow
        logger.warning("Cache store failed", extra={"error": traceback.format_exc()})
