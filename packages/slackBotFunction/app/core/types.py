"""
types for direct lambda invocation - defines contracts for bypassing slack

centralizes all type definitions for direct invocation flow to avoid scattered
inline type hints across handlers and processors.
"""

from typing import Any, TypedDict, Literal
from datetime import datetime, timezone


class DirectInvocationRequest(TypedDict, total=False):
    """payload contract for direct lambda calls - bypasses slack entirely"""

    invocation_type: Literal["direct"]
    query: str
    session_id: str | None  # conversation continuity across calls


class DirectInvocationResponseData(TypedDict):
    """successful ai response payload - matches slack handler output format"""

    text: str
    session_id: str | None
    citations: list[dict[str, str]]  # [{title: str, uri: str}, ...]
    timestamp: str  # iso8601 with Z suffix


class DirectInvocationErrorData(TypedDict):
    """error response payload - consistent structure for all failure modes"""

    error: str
    timestamp: str  # iso8601 with Z suffix


class DirectInvocationResponse(TypedDict):
    """complete lambda response envelope - includes status code + payload"""

    statusCode: int
    response: DirectInvocationResponseData | DirectInvocationErrorData


class AIProcessorResponse(TypedDict):
    """ai processor output - shared between slack and direct invocation"""

    text: str
    session_id: str | None
    citations: list[dict[str, str]]
    # TODO: ensure proper typing for bedrock response when refactoring other types in the future
    kb_response: dict[str, Any]  # raw bedrock data for slack session handling


# type guards for runtime validation
def is_valid_direct_request(event: dict[str, Any]) -> bool:
    """validate direct invocation payload structure"""
    return (
        event.get("invocation_type") == "direct"
        and isinstance(event.get("query"), str)
        and bool(event.get("query", "").strip())  # non-empty after whitespace removal
    )


def create_success_response(
    text: str, session_id: str | None, citations: list[dict[str, str]]
) -> DirectInvocationResponse:
    """factory for successful direct invocation responses"""
    return {
        "statusCode": 200,
        "response": {
            "text": text,
            "session_id": session_id,
            "citations": citations,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


def create_error_response(status_code: int, error_message: str) -> DirectInvocationResponse:
    """factory for error responses - ensures consistent timestamp format"""
    return {
        "statusCode": status_code,
        "response": {
            "error": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
