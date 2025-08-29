"""
Lambda handler for OpenSearch Serverless vector index management

This function creates and manages the vector index required by Bedrock Knowledge Base
for document embeddings and similarity search. It's typically invoked during CDK
deployment as a custom resource to set up the OpenSearch infrastructure.
"""

import json
import time
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from aws_lambda_powertools.utilities.typing import LambdaContext
from app.config.config import AWS_REGION, logger


def get_opensearch_client(endpoint):
    """
    Create authenticated OpenSearch client for Serverless or managed service
    """
    # Determine service type: AOSS (Serverless) or ES (managed)
    service = "aoss" if "aoss" in endpoint else "es"
    logger.debug(f"Connecting to OpenSearch service: {service} at {endpoint}")
    return OpenSearch(
        hosts=[{"host": endpoint, "port": 443}],
        http_auth=AWSV4SignerAuth(
            boto3.Session().get_credentials(),
            AWS_REGION,
            service,
        ),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=10,
    )


def wait_for_index_aoss(opensearch_client, index_name, timeout=300, poll_interval=5):
    """
    Wait for index to become available in OpenSearch Serverless

    AOSS has eventual consistency, so we need to poll until the index
    is fully created and mappings are available.
    """
    logger.info(f"Waiting for index '{index_name}' to be available in AOSS...")
    start = time.time()
    while True:
        try:
            if opensearch_client.indices.exists(index=index_name):
                # Verify mappings are also available (not just index existence)
                mapping = opensearch_client.indices.get_mapping(index=index_name)
                if mapping and index_name in mapping:
                    logger.info(f"Index '{index_name}' exists and mappings are ready.")
                    return True
            else:
                logger.info(f"Index '{index_name}' does not exist yet...")
        except Exception as exc:
            logger.info(f"Still waiting for index '{index_name}': {exc}")
        if time.time() - start > timeout:
            logger.error(f"Timed out waiting for index '{index_name}' to be available.")
            return False
        time.sleep(poll_interval)


def create_and_wait_for_index(client, index_name):
    """
    Create vector index with Bedrock-compatible configuration
    """
    # Index configuration optimized for Bedrock Knowledge Base
    params = {
        "index": index_name,
        "body": {
            "settings": {
                "index": {
                    "knn": True,  # Enable k-nearest neighbor search
                    "knn.algo_param.ef_search": 512,  # Search efficiency parameter
                }
            },
            "mappings": {
                "properties": {
                    # Vector field for document embeddings (1024-dim for Bedrock models)
                    "bedrock-knowledge-base-default-vector": {
                        "type": "knn_vector",
                        "dimension": 1024,  # Bedrock embedding dimension
                        "method": {
                            "name": "hnsw",  # Hierarchical Navigable Small World algorithm
                            "engine": "faiss",  # Facebook AI Similarity Search engine
                            "parameters": {},
                            "space_type": "l2",  # L2 distance for similarity
                        },
                    },
                    # Metadata field (not searchable, just stored)
                    "AMAZON_BEDROCK_METADATA": {
                        "type": "text",
                        "index": False,  # Store but don't index for search
                    },
                    # Text content field (searchable)
                    "AMAZON_BEDROCK_TEXT_CHUNK": {
                        "type": "text",
                        "index": True,  # Enable full-text search
                    },
                }
            },
        },
    }

    try:
        if not client.indices.exists(index=params["index"]):
            logger.info(f"Creating index {params['index']}")
            client.indices.create(index=params["index"], body=params["body"])
            logger.info(f"Index {params['index']} creation initiated.")
        else:
            logger.info(f"Index {params['index']} already exists")

        if not wait_for_index_aoss(client, params["index"]):
            raise RuntimeError(f"Index {params['index']} failed to appear in time")

        logger.info(f"Index {params['index']} is ready and active.")
    except Exception as e:
        logger.error(f"Error creating or waiting for index: {e}")
        raise e


def extract_parameters(event):
    """
    Extract parameters from Lambda event (CloudFormation or direct invocation)
    """
    # Handle CloudFormation custom resource format
    if "ResourceProperties" in event:
        properties = event["ResourceProperties"]
        return {
            "endpoint": properties.get("Endpoint"),
            "index_name": properties.get("IndexName"),
            "request_type": event.get("RequestType"),  # Create/Update/Delete
        }
    # Handle direct Lambda invocation format
    else:
        return {
            "endpoint": event.get("Endpoint"),
            "index_name": event.get("IndexName"),
            "request_type": event.get("RequestType"),
        }


@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict:
    """
    Main handler for OpenSearch index lifecycle management

    Handles CloudFormation custom resource events to create, update, or delete
    the vector index required by Bedrock Knowledge Base. This is typically
    called during CDK stack deployment/teardown.
    """
    logger.info("Received event", extra={"event": event})

    try:
        # Handle nested payload format (some invocation types)
        if "Payload" in event:
            event = json.loads(event["Payload"])

        params = extract_parameters(event)
        endpoint = params["endpoint"]
        index_name = params["index_name"]
        request_type = params["request_type"]

        if not endpoint or not index_name or not request_type:
            raise ValueError("Missing required parameters: Endpoint, IndexName, or RequestType")

        client = get_opensearch_client(endpoint)

        # Handle CloudFormation lifecycle events
        if request_type in ["Create", "Update"]:
            # Create or update the vector index
            create_and_wait_for_index(client, index_name)
            return {"PhysicalResourceId": f"index-{index_name}", "Status": "SUCCESS"}
        elif request_type == "Delete":
            # Clean up index during stack deletion
            try:
                if client.indices.exists(index=index_name):
                    client.indices.delete(index=index_name)
                    logger.info(f"Deleted index {index_name}")
            except Exception as e:
                # Don't fail deletion if index cleanup fails
                logger.error(f"Error deleting index: {e}")
            return {
                "PhysicalResourceId": event.get("PhysicalResourceId", f"index-{index_name}"),
                "Status": "SUCCESS",
            }
        else:
            raise ValueError(f"Invalid request type: {request_type}")

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise
