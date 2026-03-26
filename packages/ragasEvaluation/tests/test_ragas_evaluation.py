"""
Ragas quality evaluation tests for EPS Assist Me.

Runs the full evaluation pipeline against the deployed bot and asserts
that aggregate metric scores meet the configured thresholds.

Metrics:
    - faithfulness: Is the response grounded in the retrieved source context?
    - answer_relevancy: Does the response answer the question asked?
    - semantic_similarity: How close is the response to the expected reference answer?
    - answer_correctness: Is the response factually correct?

Usage:
    RAGAS_LAMBDA_FUNCTION_NAME=epsam-dev-SlackBotFunction \
    poetry run pytest packages/ragasEvaluation -m ragas -v
"""

import logging

import pytest

from evaluation.config import THRESHOLDS
from evaluation.runner import run_full_evaluation

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def evaluation_results():
    """Run the full evaluation once per module and cache results."""
    return run_full_evaluation()


@pytest.mark.ragas
class TestQualityMetrics:
    """Tests for the 4 core quality metrics."""

    def test_faithfulness_above_threshold(self, evaluation_results):
        """Responses should be grounded in the retrieved knowledge base context."""
        summary = evaluation_results.get("results", {}).get("summary", {})
        score = summary.get("faithfulness")
        if score is None:
            pytest.skip("Faithfulness metric not available in results")
        threshold = THRESHOLDS["faithfulness"]
        assert score >= threshold, f"Faithfulness score {score:.2f} below threshold {threshold:.2f}"

    def test_answer_relevancy_above_threshold(self, evaluation_results):
        """Responses should directly answer the user's question."""
        summary = evaluation_results.get("results", {}).get("summary", {})
        score = summary.get("answer_relevancy")
        if score is None:
            pytest.skip("Answer relevancy metric not available in results")
        threshold = THRESHOLDS["answer_relevancy"]
        assert score >= threshold, f"Answer relevancy score {score:.2f} below threshold {threshold:.2f}"

    def test_semantic_similarity_above_threshold(self, evaluation_results):
        """Responses should be semantically close to the expected reference answers."""
        summary = evaluation_results.get("results", {}).get("summary", {})
        score = summary.get("semantic_similarity")
        if score is None:
            pytest.skip("Semantic similarity metric not available in results")
        threshold = THRESHOLDS["semantic_similarity"]
        assert score >= threshold, f"Semantic similarity score {score:.2f} below threshold {threshold:.2f}"

    def test_answer_correctness_above_threshold(self, evaluation_results):
        """Responses should be factually correct."""
        summary = evaluation_results.get("results", {}).get("summary", {})
        score = summary.get("answer_correctness")
        if score is None:
            pytest.skip("Answer correctness metric not available in results")
        threshold = THRESHOLDS["answer_correctness"]
        assert score >= threshold, f"Answer correctness score {score:.2f} below threshold {threshold:.2f}"


@pytest.mark.ragas
class TestEvaluationHealth:
    """Meta-tests to ensure the evaluation itself ran successfully."""

    def test_all_queries_succeeded(self, evaluation_results):
        """All evaluation queries should get a response from the bot."""
        failed = evaluation_results.get("failed_queries", 0)
        total = evaluation_results.get("total_questions", 0)
        assert failed == 0, f"{failed}/{total} evaluation queries failed"

    def test_minimum_sample_count(self, evaluation_results):
        """Ensure we evaluated a meaningful number of questions."""
        successful = evaluation_results.get("successful_queries", 0)
        assert successful >= 5, f"Only {successful} queries succeeded -- need at least 5 for meaningful evaluation"
