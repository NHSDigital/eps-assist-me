"""
Configuration for Ragas quality evaluation.

All settings can be overridden via environment variables.
"""

import os


# --- AWS / Lambda Configuration ---
LAMBDA_FUNCTION_NAME = os.environ.get("RAGAS_LAMBDA_FUNCTION_NAME", "")
AWS_REGION = os.environ.get("RAGAS_AWS_REGION", "eu-west-2")

# --- Evaluator LLM ---
# Model used by Ragas to judge responses (not the bot's own model)
EVALUATOR_MODEL_ID = os.environ.get("RAGAS_EVALUATOR_MODEL_ID", "eu.anthropic.claude-3-5-sonnet-20241022-v2:0")
EVALUATOR_EMBEDDING_MODEL_ID = os.environ.get("RAGAS_EVALUATOR_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")

# --- Score Thresholds ---
# Minimum acceptable scores for each metric.  A test fails if the
# aggregate (mean) score for any metric falls below its threshold.
THRESHOLDS = {
    "faithfulness": float(os.environ.get("RAGAS_THRESHOLD_FAITHFULNESS", "0.7")),
    "answer_relevancy": float(os.environ.get("RAGAS_THRESHOLD_ANSWER_RELEVANCY", "0.7")),
    "semantic_similarity": float(os.environ.get("RAGAS_THRESHOLD_SEMANTIC_SIMILARITY", "0.7")),
    "answer_correctness": float(os.environ.get("RAGAS_THRESHOLD_ANSWER_CORRECTNESS", "0.7")),
}

# --- Output ---
RESULTS_OUTPUT_DIR = os.environ.get("RAGAS_RESULTS_DIR", "packages/ragasEvaluation/results")
