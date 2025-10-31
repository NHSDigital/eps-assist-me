import os
import traceback

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_bedrock_agent import AgentsforBedrockClient

from app.core.config import get_logger
from app.services.exceptions import PromptLoadError, PromptNotFoundError

logger = get_logger()


def load_prompt(prompt_name: str, prompt_version: str = None) -> str:
    """
    Load a prompt template from Amazon Bedrock Prompt Management.

    Resolves prompt name to ID, then loads the specified version.
    Supports both DRAFT and numbered versions.
    """
    try:
        client: AgentsforBedrockClient = boto3.client("bedrock-agent", region_name=os.environ["AWS_REGION"])

        # Get the prompt ID from the name
        prompt_id = get_prompt_id_from_name(client, prompt_name)
        if not prompt_id:
            raise PromptNotFoundError(f"Could not find prompt ID for name '{prompt_name}'")

        # Load the prompt with the specified version
        if prompt_version and prompt_version != "DRAFT":
            logger.info(
                f"Loading version {prompt_version} of prompt '{prompt_name}' (ID: {prompt_id})",
                extra={"prompt_name": prompt_name, "prompt_id": prompt_id, "prompt_version": prompt_version},
            )
            response = client.get_prompt(promptIdentifier=prompt_id, promptVersion=str(prompt_version))
        else:
            logger.info(
                f"Loading DRAFT version of prompt '{prompt_name}' (ID: {prompt_id})",
                extra={"prompt_name": prompt_name, "prompt_id": prompt_id, "prompt_version": "DRAFT"},
            )
            response = client.get_prompt(promptIdentifier=prompt_id)

        prompt_text = response["variants"][0]["templateConfiguration"]["text"]["text"]
        actual_version = response.get("version", "DRAFT")

        logger.info(
            f"Successfully loaded prompt '{prompt_name}' version {actual_version}",
            extra={
                "prompt_name": prompt_name,
                "prompt_id": prompt_id,
                "version_used": actual_version,
            },
        )
        return prompt_text

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        logger.error(
            f"Failed to load prompt '{prompt_name}' version '{prompt_version}': {error_code} - {error_message}",
            extra={
                "prompt_name": prompt_name,
                "error_code": error_code,
                "requested_version": prompt_version,
                "error": traceback.format_exc(),
            },
        )
        raise PromptLoadError(
            f"Failed to load prompt '{prompt_name}' version '{prompt_version}': {error_code} - {error_message}"
        ) from e

    except Exception as e:
        logger.error(
            "Unexpected error loading prompt",
            extra={"prompt_name": prompt_name, "error_type": type(e).__name__, "error": traceback.format_exc()},
        )
        raise PromptLoadError(f"Unexpected error loading prompt '{prompt_name}': {e}") from e


def get_prompt_id_from_name(client: AgentsforBedrockClient, prompt_name: str) -> str | None:
    """
    Get the 10-character prompt ID from the prompt name using ListPrompts.
    """
    try:
        response = client.list_prompts(maxResults=50)

        for prompt in response.get("promptSummaries", []):
            if prompt.get("name") == prompt_name:
                prompt_id = prompt.get("id")
                logger.info("Found prompt ID for name", extra={"prompt_id": prompt_id, "prompt_name": prompt_name})
                return prompt_id

        logger.error("No prompt found with name", extra={"prompt_name": prompt_name})
        return None

    except ClientError:
        logger.error("Failed to list prompts", extra={"error": traceback.format_exc()})
        return None
