import os
import traceback
import boto3
from botocore.exceptions import ClientError
from app.core.config import get_logger
from app.services.exceptions import PromptNotFoundError, PromptLoadError
from mypy_boto3_bedrock_agent import AgentsforBedrockClient

logger = get_logger()


def _render_prompt(template_config: dict) -> str:
    """
    Returns a unified prompt string regardless of template type.
    """

    chat_cfg = template_config.get("chat")
    if chat_cfg:
        parts: list[str] = []

        system_items = chat_cfg.get("system", [])
        logger.debug("Processing system messages for prompt rendering", extra={"system_items": system_items})
        if isinstance(system_items, list):
            system_texts = [
                item["text"].strip()
                for item in system_items
                if isinstance(item, dict) and "text" in item and item["text"].strip()
            ]
            if system_texts:
                parts.append("\n".join(system_texts))

        role_prefix = {
            "user": "Human: ",
            "assistant": "Assistant: ",
        }

        logger.debug("Processing chat messages for prompt rendering", extra={"messages": chat_cfg.get("messages", [])})

        for msg in chat_cfg.get("messages", []):
            role = (msg.get("role") or "").lower()
            prefix = role_prefix.get(role)
            if not prefix:
                continue

            content_items = msg.get("content", [])
            content_texts = [
                item["text"].strip()
                for item in content_items
                if isinstance(item, dict) and "text" in item and item["text"].strip()
            ]

            if content_texts:
                parts.append(prefix + "\n".join(content_texts))

        return "\n\n".join(parts)

    text_cfg = template_config.get("text")
    if isinstance(text_cfg, dict) and "text" in text_cfg:
        return text_cfg["text"]
    if isinstance(text_cfg, str):
        return text_cfg

    logger.error(
        "Unsupported prompt configuration encountered",
        extra={"available_keys": list(template_config.keys())},
    )
    raise PromptLoadError(f"Unsupported prompt configuration. Keys: {list(template_config.keys())}")


def load_prompt(prompt_name: str, prompt_version: str = None) -> str:
    """
    Load a prompt template from Amazon Bedrock Prompt Management.

    Resolves prompt name to ID, then loads the specified version.
    Supports both DRAFT and numbered versions.
    Handles both text and chat prompt templates.
    """
    try:
        client: AgentsforBedrockClient = boto3.client("bedrock-agent", region_name=os.environ["AWS_REGION"])

        # Get the prompt ID from the name
        prompt_id = get_prompt_id_from_name(client, prompt_name)
        if not prompt_id:
            raise PromptNotFoundError(f"Could not find prompt ID for name '{prompt_name}'")

        is_explicit_version = prompt_version and prompt_version != "DRAFT"
        selected_version = str(prompt_version) if is_explicit_version else "DRAFT"

        logger.info(
            f"Loading prompt {prompt_name}' (ID: {prompt_id})",
            extra={"prompt_name": prompt_name, "prompt_id": prompt_id, "prompt_version": prompt_version},
        )

        if is_explicit_version:
            response = client.get_prompt(promptIdentifier=prompt_id, promptVersion=selected_version)
        else:
            response = client.get_prompt(promptIdentifier=prompt_id)

        template_config = response["variants"][0]["templateConfiguration"]
        prompt_text = _render_prompt(template_config)
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
        )

    except Exception as e:
        logger.error(
            "Unexpected error loading prompt",
            extra={"prompt_name": prompt_name, "error_type": type(e).__name__, "error": traceback.format_exc()},
        )
        raise PromptLoadError(f"Unexpected error loading prompt '{prompt_name}': {e}")


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
