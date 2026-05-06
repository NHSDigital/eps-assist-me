"""DeepEval pytest suite for the EPS chatbot.

Smoke (PR gate):  pytest -m smoke, ~3 cases, faithfulness + answer relevancy.
Full (deploy gate): pytest, all cases, all 4 metrics.

Thresholds are placeholders, calibrate against human-labelled data before
using this gate to block real deploys.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase

from evaluation.chatbot import get_chatbot_response

THRESHOLDS = {
    "faithfulness": 0.8,
    "answer_relevancy": 0.8,
    "contextual_precision": 0.7,
    "contextual_recall": 0.7,
}

_DATASET_PATH = Path(__file__).resolve().parent.parent / "test_cases.json"
ALL_CASES: list[dict] = json.loads(_DATASET_PATH.read_text())
SMOKE_CASES: list[dict] = [c for c in ALL_CASES if c.get("smoke", False)]


def _build_llm_test_case(case: dict) -> LLMTestCase:
    answer, retrieved_contexts = get_chatbot_response(case["query"])
    return LLMTestCase(
        input=case["query"],
        actual_output=answer,
        retrieval_context=retrieved_contexts,
        expected_output=case["ground_truth"],
    )


@pytest.mark.smoke
@pytest.mark.parametrize("case", SMOKE_CASES, ids=[c["id"] for c in SMOKE_CASES])
def test_smoke(case: dict, judge_model) -> None:
    """Fast PR gate, faithfulness + answer relevancy only."""
    llm_case = _build_llm_test_case(case)
    assert_test(
        llm_case,
        metrics=[
            FaithfulnessMetric(
                model=judge_model,
                threshold=THRESHOLDS["faithfulness"],
            ),
            AnswerRelevancyMetric(
                model=judge_model,
                threshold=THRESHOLDS["answer_relevancy"],
            ),
        ],
    )


@pytest.mark.parametrize("case", ALL_CASES, ids=[c["id"] for c in ALL_CASES])
def test_full(case: dict, judge_model) -> None:
    """Full deploy gate, all four RAG quality metrics.

    Cases with skip_contextual: true only get faithfulness + answer relevancy
    (for questions answered via reasoning rather than a specific KB document).
    """
    llm_case = _build_llm_test_case(case)

    metrics = [
        FaithfulnessMetric(
            model=judge_model,
            threshold=THRESHOLDS["faithfulness"],
        ),
        AnswerRelevancyMetric(
            model=judge_model,
            threshold=THRESHOLDS["answer_relevancy"],
        ),
    ]

    if not case.get("skip_contextual", False):
        metrics.extend(
            [
                ContextualPrecisionMetric(
                    model=judge_model,
                    threshold=THRESHOLDS["contextual_precision"],
                ),
                ContextualRecallMetric(
                    model=judge_model,
                    threshold=THRESHOLDS["contextual_recall"],
                ),
            ]
        )

    assert_test(llm_case, metrics=metrics)
