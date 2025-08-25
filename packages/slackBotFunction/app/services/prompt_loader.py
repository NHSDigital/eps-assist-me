import os
import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

logger = Logger(service="promptLoader")


def load_prompt(prompt_name: str, prompt_version: str = None) -> str:
    """
    Load a prompt template from Amazon Bedrock Prompt Management.

    Resolves prompt name to ID, then loads the specified version.
    Supports both DRAFT and numbered versions.

    Args:
        prompt_name: The human-readable name of the prompt
        prompt_version: Version to load - "DRAFT" for latest draft, number for published version,
                       None for default behavior (loads DRAFT)
    """
    try:
        client = boto3.client("bedrock-agent", region_name=os.environ["AWS_REGION"])

        # Get the prompt ID from the name
        prompt_id = get_prompt_id_from_name(client, prompt_name)
        if not prompt_id:
            raise Exception(f"Could not find prompt ID for name '{prompt_name}'")

        # Load the prompt with the specified version
        if prompt_version == "DRAFT":
            logger.info(
                f"Loading DRAFT version of prompt '{prompt_name}' (ID: {prompt_id})",
                extra={"prompt_name": prompt_name, "prompt_id": prompt_id, "prompt_version": "DRAFT"},
            )
            response = client.get_prompt(promptIdentifier=prompt_id)
        else:
            logger.info(
                f"Loading version {prompt_version} of prompt '{prompt_name}' (ID: {prompt_id})",
                extra={"prompt_name": prompt_name, "prompt_id": prompt_id, "prompt_version": prompt_version},
            )
            response = client.get_prompt(promptIdentifier=prompt_id, promptVersion=str(prompt_version))

        prompt_text = response["variants"][0]["templateConfiguration"]["text"]["text"]
        actual_version = response.get("version", "DRAFT")

        logger.info(
            f"Successfully loaded prompt '{prompt_name}' version {actual_version}",
            extra={
                "prompt_name": prompt_name,
                "prompt_id": prompt_id,
                "version_requested": prompt_version,
                "version_actual": actual_version,
                "selection_method": "default" if prompt_version is None else "explicit",
            },
        )
        return prompt_text

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        logger.error(
            f"Failed to load prompt '{prompt_name}' version '{prompt_version}': {error_code} - {error_message}",
            extra={"prompt_name": prompt_name, "error_code": error_code, "requested_version": prompt_version},
        )
        raise Exception(
            f"Failed to load prompt '{prompt_name}' version '{prompt_version}': {error_code} - {error_message}"
        )

    except Exception as e:
        logger.error(f"Unexpected error loading prompt '{prompt_name}': {e}")
        raise Exception(f"Unexpected error loading prompt '{prompt_name}': {e}")


def get_prompt_id_from_name(client, prompt_name: str) -> str:
    """
    Get the 10-character prompt ID from the prompt name using ListPrompts.
    """
    try:
        response = client.list_prompts(maxResults=50)

        for prompt in response.get("promptSummaries", []):
            if prompt.get("name") == prompt_name:
                prompt_id = prompt.get("id")
                logger.info(f"Found prompt ID '{prompt_id}' for name '{prompt_name}'")
                return prompt_id

        logger.error(f"No prompt found with name '{prompt_name}'")
        return None

    except ClientError as e:
        logger.error(f"Failed to list prompts: {e}")
        return None
