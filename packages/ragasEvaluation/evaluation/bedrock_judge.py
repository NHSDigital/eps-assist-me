"""Custom DeepEval judge model backed by AWS Bedrock.

Uses boto3 converse API directly instead of DeepEval's built-in
AmazonBedrockModel, which requires aiobotocore (incompatible botocore pins).

Usage::

    from evaluation.bedrock_judge import BedrockJudgeModel
    model = BedrockJudgeModel() defaults to Amazon Nova Pro in eu-west-2
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from deepeval.models import DeepEvalBaseLLM
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_ID = "amazon.nova-pro-v1:0"
_DEFAULT_REGION = "eu-west-2"


class BedrockJudgeModel(DeepEvalBaseLLM):
    """DeepEval LLM judge that calls AWS Bedrock via the converse API."""

    def __init__(
        self,
        model_id: str | None = None,
        region: str | None = None,
    ) -> None:
        self.model_id = model_id or os.environ.get("DEEPEVAL_JUDGE_MODEL", _DEFAULT_MODEL_ID)
        self.region = region or os.environ.get("AWS_REGION", _DEFAULT_REGION)
        self._client = boto3.client("bedrock-runtime", region_name=self.region)
        super().__init__(model=self.model_id)

    def load_model(self) -> "BedrockJudgeModel":
        return self

    def get_model_name(self) -> str:
        return self.model_id

    def _call_bedrock(self, prompt: str) -> str:
        response = self._client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 4096, "temperature": 0},
        )
        return response["output"]["message"]["content"][0]["text"]

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        if "```json" in text:
            return text.split("```json")[1].split("```")[0].strip()
        if "```" in text:
            return text.split("```")[1].split("```")[0].strip()
        return text.strip()

    def generate(self, prompt: str, schema: type[BaseModel] | None = None) -> Any:
        """Generate a response, optionally validated against a pydantic schema."""
        if schema:
            schema_json = json.dumps(schema.model_json_schema())
            prompt = f"{prompt}\n\nRespond ONLY with valid JSON matching this schema:\n{schema_json}"

        text = self._call_bedrock(prompt)

        if schema:
            try:
                return schema.model_validate_json(self._strip_markdown_fences(text))
            except Exception:
                logger.warning("Failed to parse JSON response, retrying", exc_info=True)
                retry_prompt = (
                    f"{prompt}\n\nYour previous response was not valid JSON. "
                    f"Please respond with ONLY valid JSON, no markdown formatting."
                )
                text = self._call_bedrock(retry_prompt)
                return schema.model_validate_json(self._strip_markdown_fences(text))

        return text

    async def a_generate(self, prompt: str, schema: type[BaseModel] | None = None) -> Any:
        """Async shim, boto3 is synchronous so this just delegates."""
        return self.generate(prompt, schema)
