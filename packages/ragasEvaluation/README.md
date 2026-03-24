# Ragas Quality Evaluation for EPS Assist Me

Automated post-deployment quality evaluation of the EPS Assist Me AI bot using the [Ragas](https://docs.ragas.io/) framework.

## Overview

After each deployment, this evaluation suite invokes the deployed Slack Bot Lambda directly (bypassing Slack) and evaluates the AI responses against a curated dataset of EPS onboarding questions using LLM-as-a-judge metrics.

## Metrics

| Metric | Description |
|--------|-------------|
| **Faithfulness** | Is the response grounded in the retrieved knowledge base source context? |
| **Answer Relevancy** | Does the response actually answer the question that was asked? |
| **Semantic Similarity** | How close is the response to the expected reference answer? |
| **Answer Correctness** | Is the response factually correct? (combines faithfulness + similarity) |

## Running Locally

```bash
# Requires AWS credentials with Lambda invoke permissions
export RAGAS_LAMBDA_FUNCTION_NAME="epsam-dev-SlackBotFunction"
export RAGAS_AWS_REGION="eu-west-2"
export RAGAS_EVALUATOR_MODEL_ID="eu.anthropic.claude-3-5-sonnet-20241022-v2:0"

cd /workspaces/eps-assist-me
poetry run pytest packages/ragasEvaluation -m ragas -v
```

## Test Dataset

The evaluation dataset is defined in `evaluation/test_dataset.py` and contains representative EPS onboarding questions covering:

- Prescription ID generation and structure
- CIS2 authentication requirements
- RBAC controls for prescribers
- Repeat dispensing cancellation scenarios
- Controlled drug prescribing rules
- FHIR API schema requirements
- Nomination management
- Error handling guidance

## CI/CD Integration

The evaluation runs automatically in the `release_all_stacks.yml` workflow after successful deployment, gated by the `RUN_RAGAS_EVALUATION` input.

## Thresholds

The evaluation enforces minimum score thresholds (configurable in `evaluation/config.py`):

- Faithfulness: >= 0.7
- Answer Relevancy: >= 0.7
- Semantic Similarity: >= 0.7
- Answer Correctness: >= 0.7
