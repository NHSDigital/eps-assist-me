"""
Core evaluation runner.

Orchestrates:
1. Invoking the deployed bot for each question in the dataset
2. Building Ragas SingleTurnSample objects with response + retrieved contexts + reference
3. Running Ragas evaluate() with 4 metrics: faithfulness, relevancy, similarity, correctness
4. Persisting results to JSON for CI reporting
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Python 3.14 compatibility patch
# ---------------------------------------------------------------------------
# nest_asyncio (used internally by Ragas) patches asyncio's _run_once to pop
# the current task from _current_tasks before executing each handle. On Python
# 3.14+, asyncio.wait_for() -> asyncio.timeout() now raises
#   RuntimeError("Timeout should be used inside a task")
# because the current task has been temporarily removed by nest_asyncio.
#
# We monkey-patch asyncio.wait_for *before* importing Ragas so the patched
# version is picked up everywhere.  The patch simply falls back to awaiting
# the coroutine without a timeout when the RuntimeError is raised.
# ---------------------------------------------------------------------------
if sys.version_info >= (3, 14):
    _original_wait_for = asyncio.wait_for

    async def _patched_wait_for(fut, timeout, **kwargs):
        try:
            return await _original_wait_for(fut, timeout, **kwargs)
        except RuntimeError as exc:
            if "Timeout should be used inside a task" in str(exc):
                return await fut
            raise

    asyncio.wait_for = _patched_wait_for

import nest_asyncio  # noqa: E402  – must come after the patch above
from ragas import evaluate  # noqa: E402
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample  # noqa: E402

from evaluation.config import RESULTS_OUTPUT_DIR  # noqa: E402
from evaluation.lambda_invoker import invoke_bot  # noqa: E402
from evaluation.metrics import get_metrics  # noqa: E402
from evaluation.test_dataset import EVALUATION_DATASET  # noqa: E402

nest_asyncio.apply()

logger = logging.getLogger(__name__)


def _extract_citation_texts(citations: list[dict]) -> list[str]:
    """
    Extract retrieved context strings from Bedrock citation format.

    Bedrock returns citations as a list of objects with retrievedReferences
    containing content->text.  We flatten to a list of strings.
    """
    contexts: list[str] = []
    for citation_group in citations:
        refs = citation_group.get("retrievedReferences", [])
        for ref in refs:
            text = ref.get("content", {}).get("text", "")
            if text:
                contexts.append(text)
    return contexts


def collect_responses() -> list[dict]:
    """
    Invoke the bot for every question in the dataset and collect responses.

    Returns a list of dicts with keys:
        user_input, reference, category, response_text, retrieved_contexts, session_id
    """
    results = []
    for item in EVALUATION_DATASET:
        query = item["user_input"]
        try:
            response = invoke_bot(query)
            retrieved_contexts = _extract_citation_texts(response.get("citations", []))
            results.append(
                {
                    "user_input": query,
                    "reference": item["reference"],
                    "category": item["category"],
                    "response_text": response["text"],
                    "retrieved_contexts": retrieved_contexts,
                    "session_id": response.get("session_id"),
                }
            )
        except Exception:
            logger.exception("Failed to get response for query: %s", query[:80])
            results.append(
                {
                    "user_input": query,
                    "reference": item["reference"],
                    "category": item["category"],
                    "response_text": "",
                    "retrieved_contexts": [],
                    "session_id": None,
                    "error": True,
                }
            )
    return results


def build_single_turn_samples(responses: list[dict]) -> list[SingleTurnSample]:
    """Build Ragas SingleTurnSample objects for RAG metric evaluation."""
    samples = []
    for r in responses:
        if r.get("error"):
            continue
        samples.append(
            SingleTurnSample(
                user_input=r["user_input"],
                response=r["response_text"],
                retrieved_contexts=r["retrieved_contexts"] if r["retrieved_contexts"] else ["No context retrieved."],
                reference=r["reference"],
            )
        )
    return samples


def run_evaluation(responses: list[dict]) -> dict:
    """Run all 4 metrics: faithfulness, relevancy, similarity, correctness."""
    samples = build_single_turn_samples(responses)
    if not samples:
        logger.warning("No valid samples for evaluation")
        return {}

    metrics = get_metrics()
    dataset = EvaluationDataset(samples=samples)

    logger.info("Running evaluation with %d samples and %d metrics", len(samples), len(metrics))
    result = evaluate(dataset=dataset, metrics=metrics)

    df = result.to_pandas()
    return {
        "scores": result.scores.to_dict() if hasattr(result.scores, "to_dict") else {},
        "summary": {
            col: float(df[col].mean())
            for col in df.columns
            if col not in ("user_input", "reference", "response", "retrieved_contexts")
        },
    }


def run_full_evaluation() -> dict:
    """
    Run the complete evaluation pipeline:
    1. Collect bot responses
    2. Evaluate with all 4 metrics (faithfulness, relevancy, similarity, correctness)
    3. Persist results

    Returns combined results dict.
    """
    logger.info("Starting Ragas evaluation with %d questions", len(EVALUATION_DATASET))

    responses = collect_responses()
    error_count = sum(1 for r in responses if r.get("error"))
    if error_count:
        logger.warning("%d/%d queries failed", error_count, len(responses))

    evaluation_results = run_evaluation(responses)

    combined = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_questions": len(EVALUATION_DATASET),
        "successful_queries": len(responses) - error_count,
        "failed_queries": error_count,
        "results": evaluation_results,
    }

    _persist_results(combined, responses)

    return combined


def _persist_results(results: dict, responses: list[dict]) -> None:
    """Write evaluation results and raw responses to JSON files."""
    output_dir = Path(RESULTS_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    results_path = output_dir / f"evaluation_{run_id}.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Results written to %s", results_path)

    responses_path = output_dir / f"responses_{run_id}.json"
    with open(responses_path, "w") as f:
        json.dump(responses, f, indent=2, default=str)
    logger.info("Responses written to %s", responses_path)
