import json
import logging
import os
import time

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_opensearch_client(endpoint):
    service = "aoss" if "aoss" in endpoint else "es"
    logger.debug(f"Connecting to OpenSearch service: {service} at {endpoint}")
    return OpenSearch(
        hosts=[
            {
                "host": endpoint,
                "port": 443,
            }
        ],
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


def wait_for_index(opensearch_client, index_name, timeout=120, poll_interval=5):
    """
    Waits for the OpenSearch index to exist and be at least 'yellow' health.
    """
    logger.info(f"Polling for index '{index_name}' to exist and be ready...")
    start = time.time()
    while True:
        try:
            if opensearch_client.indices.exists(index=index_name):
                health = opensearch_client.cluster.health(index=index_name, wait_for_status="yellow", timeout="5s")
                status = health.get("status")
                logger.info(f"Index '{index_name}' exists, health: {status}")
                if status in ("yellow", "green"):
                    return True
            else:
                logger.info(f"Index '{index_name}' does not exist yet...")
        except Exception as exc:
            logger.warning(f"Error checking index status: {exc}")

        if time.time() - start > timeout:
            logger.error(f"Timed out waiting for index '{index_name}' to become ready.")
            return False

        time.sleep(poll_interval)


def create_and_wait_for_index(client, index_name):
    """Create the index and wait for it to be ready"""
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
        # Check if index exists first
        if not client.indices.exists(index=params["index"]):
            logger.info(f"Creating index {params['index']}")
            client.indices.create(
                index=params["index"], body=params["body"]
            )
            logger.info(f"Index {params['index']} creation initiated.")
        else:
            logger.info(f"Index {params['index']} already exists")

        # Wait for the index to be available and ready
        if not wait_for_index(client, params["index"]):
            raise Exception(f"Index {params['index']} failed to become ready in time")

        logger.info(f"Index {params['index']} is ready and active.")
    except Exception as e:
        logger.error(f"Error creating or waiting for index: {e}")
        raise e  # Re-raise to fail the custom resource


def extract_parameters(event):
    """Extract parameters from the event"""
    if "ResourceProperties" in event:
        # CloudFormation custom resource event
        properties = event["ResourceProperties"]
        return {
            "endpoint": properties.get("Endpoint"),
            "index_name": properties.get("IndexName"),
            "request_type": event.get("RequestType")
        }
    else:
        # Direct Lambda invocation
        return {
            "endpoint": event.get("Endpoint"),
            "index_name": event.get("IndexName"),
            "request_type": event.get("RequestType")
        }


def handler(event, context):
    """Main Lambda handler function"""
    logger.info("Received event: %s", json.dumps(event, indent=2))

    try:
        # Handle CloudFormation custom resource wrapped in Lambda invoke
        if "Payload" in event:
            event = json.loads(event["Payload"])

        # Extract parameters
        params = extract_parameters(event)
        endpoint = params["endpoint"]
        index_name = params["index_name"]
        request_type = params["request_type"]

        if not endpoint or not index_name or not request_type:
            raise ValueError("Missing required parameters: Endpoint, IndexName, or RequestType")

        client = get_opensearch_client(endpoint)

        if request_type in ["Create", "Update"]:
            create_and_wait_for_index(client, index_name)
            return {
                "PhysicalResourceId": f"index-{index_name}",
                "Status": "SUCCESS"
            }
        elif request_type == "Delete":
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
