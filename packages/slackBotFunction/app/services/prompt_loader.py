import os
import boto3
from aws_lambda_powertools import Logger

logger = Logger(service="promptLoader")


def load_prompt(prompt_name: str, version: str = "$LATEST") -> str:
    """
    Load a prompt template from Amazon Bedrock Prompt Management.
    """
    try:
        client = boto3.client("bedrock-agent", region_name=os.environ["AWS_REGION"])

        response = client.get_prompt(promptIdentifier=prompt_name, promptVersion=version)

        return response["variants"][0]["templateConfiguration"]["text"]["text"]

    except Exception as e:
        logger.error(f"Error loading prompt {prompt_name}: {e}")
        raise
