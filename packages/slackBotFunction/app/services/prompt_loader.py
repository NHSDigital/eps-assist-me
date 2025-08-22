import os
import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

logger = Logger(service="promptLoader")


def _test_list_prompts(client):
    """Test listing prompts."""
    try:
        response = client.list_prompts(maxResults=10)
        logger.info(f"✅ ListPrompts SUCCEEDED: Found {len(response.get('promptSummaries', []))} prompts")
        for prompt in response.get("promptSummaries", []):
            logger.info(f"   - Prompt: {prompt.get('name')} (ID: {prompt.get('id')})")
    except ClientError as e:
        logger.error(f"❌ ListPrompts FAILED: {e}")


def _test_get_prompt(client, prompt_name):
    """Test getting a specific prompt."""
    try:
        response = client.get_prompt(promptIdentifier=prompt_name, promptVersion="$LATEST")
        logger.info(f"✅ GetPrompt SUCCEEDED for {prompt_name}: {len(response.get('variants', []))} variants")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logger.error(f"❌ GetPrompt FAILED for {prompt_name}: {error_code} - {error_message}")
        _test_alternative_prompts(client)


def _test_alternative_prompts(client):
    """Test getting prompts with different identifiers."""
    list_response = client.list_prompts(maxResults=10)
    for prompt in list_response.get("promptSummaries", []):
        try:
            prompt_id = prompt.get("id")
            test_response = client.get_prompt(promptIdentifier=prompt_id, promptVersion="$LATEST")
            logger.info(
                f"✅ GetPrompt SUCCEEDED for prompt ID {prompt_id}: {len(test_response.get('variants', []))} variants"
            )
            break
        except ClientError as e2:
            logger.error(f"❌ GetPrompt FAILED for prompt ID {prompt_id}: {e2}")


def _analyze_iam_permissions():
    """Analyze IAM permissions for the current role."""
    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        logger.info(f"Lambda running as: {identity.get('Arn')}")

        role_arn = identity.get("Arn")
        if "assumed-role" in role_arn:
            role_name = role_arn.split("/")[-2]
            iam = boto3.client("iam")

            try:
                attached_policies = iam.list_attached_role_policies(RoleName=role_name)
                logger.info("Attached managed policies:")
                for policy in attached_policies.get("AttachedPolicies", []):
                    logger.info(f"   - {policy.get('PolicyName')} ({policy.get('PolicyArn')})")
            except Exception as e:
                logger.warning(f"Could not list attached policies: {e}")
    except Exception as e:
        logger.warning(f"Could not analyze IAM permissions: {e}")


def debug_bedrock_permissions():
    """Debug Bedrock operations and permissions."""
    try:
        logger.info(f"AWS_REGION: {os.environ.get('AWS_REGION')}")
        logger.info(f"QUERY_REFORMULATION_PROMPT_NAME: {os.environ.get('QUERY_REFORMULATION_PROMPT_NAME')}")

        client = boto3.client("bedrock-agent", region_name=os.environ["AWS_REGION"])
        logger.info("Testing Bedrock Agent permissions...")

        _test_list_prompts(client)
        prompt_name = os.environ.get("QUERY_REFORMULATION_PROMPT_NAME", "epsam-pr-27-queryReformulation")
        _test_get_prompt(client, prompt_name)
        _analyze_iam_permissions()

    except Exception as e:
        logger.error(f"Debug permissions test failed: {e}")


def load_prompt(prompt_name: str, version: str = "$LATEST") -> str:
    """
    Load a prompt template from Amazon Bedrock Prompt Management.
    Includes debugging to help understand permission issues.
    """

    # Run debug test on first call
    if not hasattr(load_prompt, "_debug_run"):
        debug_bedrock_permissions()
        load_prompt._debug_run = True

    try:
        client = boto3.client("bedrock-agent", region_name=os.environ["AWS_REGION"])
        response = client.get_prompt(promptIdentifier=prompt_name, promptVersion=version)
        prompt_text = response["variants"][0]["templateConfiguration"]["text"]["text"]

        logger.info(f"Successfully loaded prompt '{prompt_name}' version '{version}'")
        return prompt_text

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        logger.error(f"Failed to load prompt '{prompt_name}': {error_code} - {error_message}")
        logger.info("This appears to be the known AWS Bedrock Prompt Management issue affecting multiple users")

        raise Exception(f"Failed to load prompt '{prompt_name}': {error_code} - {error_message}")

    except Exception as e:
        logger.error(f"Unexpected error loading prompt '{prompt_name}': {e}")
        raise Exception(f"Unexpected error loading prompt '{prompt_name}': {e}")
