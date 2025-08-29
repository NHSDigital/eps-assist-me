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
    logger.debug("Connecting to OpenSearch service", extra={"service": service, "endpoint": endpoint})
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
    logger.info("Waiting for index to be available in AOSS", extra={"index_name": index_name})
    start = time.time()
    while True:
        try:
            if opensearch_client.indices.exists(index=index_name):
                # Verify mappings are also available (not just index existence)
                mapping = opensearch_client.indices.get_mapping(index=index_name)
                if mapping and index_name in mapping:
                    logger.info("Index exists and mappings are ready", extra={"index_name": index_name})
                    return True
            else:
                logger.info("Index does not exist yet", extra={"index_name": index_name})
        except Exception as exc:
            logger.info("Still waiting for index", extra={"index_name": index_name, "error": str(exc)})
        if time.time() - start > timeout:
            logger.error("Timed out waiting for index to be available", extra={"index_name": index_name})
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
            logger.info("Creating index", extra={"index_name": params["index"]})
            client.indices.create(index=params["index"], body=params["body"])
            logger.info("Index creation initiated", extra={"index_name": params["index"]})
        else:
            logger.info("Index already exists", extra={"index_name": params["index"]})

        if not wait_for_index_aoss(client, params["index"]):
            raise RuntimeError(f"Index {params['index']} failed to appear in time")

        logger.info("Index is ready and active", extra={"index_name": params["index"]})
    except Exception as e:
        logger.error("Error creating or waiting for index", extra={"error": str(e)})
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
                    logger.info("Deleted index", extra={"index_name": index_name})
            except Exception as e:
                # Don't fail deletion if index cleanup fails
                logger.error("Error deleting index", extra={"error": str(e)})
            return {
                "PhysicalResourceId": event.get("PhysicalResourceId", f"index-{index_name}"),
                "Status": "SUCCESS",
            }
        else:
            raise ValueError(f"Invalid request type: {request_type}")

    except Exception as e:
        logger.error("Error processing request", extra={"error": str(e)})
        raise
