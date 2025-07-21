import json
import logging
import os
import time

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_opensearch_client(endpoint):
    """
    Create an OpenSearch (AOSS) client using AWS credentials.
    Works for both AOSS and legacy OpenSearch domains by checking the endpoint.
    """
    service = "aoss" if "aoss" in endpoint else "es"
    # Remove protocol, because the OpenSearch client expects only the host part.
    endpoint = endpoint.replace("https://", "").replace("http://", "")
    logger.debug(f"Connecting to OpenSearch service: {service} at {endpoint}")
    return OpenSearch(
        hosts=[{"host": endpoint, "port": 443}],
        http_auth=AWSV4SignerAuth(
            boto3.Session().get_credentials(),
            os.getenv("AWS_REGION", "eu-west-2"),
            service,
        ),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=10,
    )


def wait_for_index_aoss(opensearch_client, index_name, timeout=60, poll_interval=3):
    """
    Wait until the index exists in OpenSearch Serverless (AOSS).
    AOSS does not support cluster health checks, so existence == ready.
    """
    logger.info(f"Waiting for index '{index_name}' to exist in AOSS...")
    start = time.time()
    while True:
        try:
            # HEAD API: Does the index exist yet?
            if opensearch_client.indices.exists(index=index_name):
                logger.info(f"Index '{index_name}' exists and is considered ready (AOSS).")
                return True
            else:
                logger.info(f"Index '{index_name}' does not exist yet...")
        except Exception as exc:
            logger.warning(f"Error checking index existence: {exc}")
        # Exit on timeout to avoid infinite loop during stack failures.
        if time.time() - start > timeout:
            logger.error(f"Timed out waiting for index '{index_name}' to exist.")
            return False
        time.sleep(poll_interval)


def create_and_wait_for_index(client, index_name):
    """
    Creates the index (if not present) and waits until it's ready for use.
    Idempotent: Does nothing if the index is already present.
    """
    params = {
        "index": index_name,
        "body": {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 512,
                }
            },
            "mappings": {
                "properties": {
                    "bedrock-knowledge-base-default-vector": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "engine": "faiss",
                            "parameters": {},
                            "space_type": "l2",
                        },
                    },
                    "AMAZON_BEDROCK_METADATA": {
                        "type": "text",
                        "index": "false",
                    },
                    "AMAZON_BEDROCK_TEXT_CHUNK": {
                        "type": "text",
                        "index": "true",
                    },
                }
            },
        },
    }

    try:
        # Only create if not present (safe for repeat runs/rollbacks)
        if not client.indices.exists(index=params["index"]):
            logger.info(f"Creating index {params['index']}")
            client.indices.create(index=params["index"], body=params["body"])
            logger.info(f"Index {params['index']} creation initiated.")
        else:
            logger.info(f"Index {params['index']} already exists")

        # Wait until available for downstream resources
        if not wait_for_index_aoss(client, params["index"]):
            raise Exception(f"Index {params['index']} failed to appear in time")

        logger.info(f"Index {params['index']} is ready and active.")
    except Exception as e:
        logger.error(f"Error creating or waiting for index: {e}")
        raise e  # Fail stack if this fails


def extract_parameters(event):
    """
    Extract parameters from Lambda event, handling both:
      - CloudFormation custom resource invocations
      - Direct Lambda/test calls
    """
    if "ResourceProperties" in event:
        # From CloudFormation custom resource
        properties = event["ResourceProperties"]
        return {
            "endpoint": properties.get("Endpoint"),
            "index_name": properties.get("IndexName"),
            "request_type": event.get("RequestType")
        }
    else:
        # From direct Lambda invocation (e.g., manual test)
        return {
            "endpoint": event.get("Endpoint"),
            "index_name": event.get("IndexName"),
            "request_type": event.get("RequestType")
        }


def handler(event, context):
    """
    Entrypoint: create, update, or delete the OpenSearch index.
    Invoked via CloudFormation custom resource or manually.
    """
    logger.info("Received event: %s", json.dumps(event, indent=2))

    try:
        # CloudFormation custom resources may pass the actual event as a JSON string in "Payload"
        if "Payload" in event:
            event = json.loads(event["Payload"])

        # Get parameters (handles both invocation types)
        params = extract_parameters(event)
        endpoint = params["endpoint"]
        index_name = params["index_name"]
        request_type = params["request_type"]

        # Sanity check required parameters
        if not endpoint or not index_name or not request_type:
            raise ValueError("Missing required parameters: Endpoint, IndexName, or RequestType")

        client = get_opensearch_client(endpoint)

        if request_type in ["Create", "Update"]:
            # Idempotent: will not fail if index already exists
            create_and_wait_for_index(client, index_name)
            return {
                "PhysicalResourceId": f"index-{index_name}",
                "Status": "SUCCESS"
            }
        elif request_type == "Delete":
            # Clean up the index if it exists
            try:
                if client.indices.exists(index=index_name):
                    client.indices.delete(index=index_name)
                    logger.info(f"Deleted index {index_name}")
            except Exception as e:
                logger.error(f"Error deleting index: {e}")
            return {
                "PhysicalResourceId": event.get("PhysicalResourceId", f"index-{index_name}"),
                "Status": "SUCCESS"
            }
        else:
            raise ValueError(f"Invalid request type: {request_type}")

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise
