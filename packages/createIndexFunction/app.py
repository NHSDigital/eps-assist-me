import json
import logging
import os
import time

import boto3
from botocore.exceptions import NoCredentialsError
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
            os.getenv("AWS_REGION"),
            service,
        ),
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=10,
    )


def wait_for_index(opensearch_client, index_name, timeout=120, poll_interval=4):
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
                    return
            else:
                logger.info(f"Index '{index_name}' does not exist yet...")
        except Exception as exc:
            logger.info(f"Error checking index status: {exc}")
        if time.time() - start > timeout:
            raise TimeoutError(f"Timed out waiting for index '{index_name}' to become ready.")
        time.sleep(poll_interval)


def handler(event, context):
    logger.info("Received event: %s", json.dumps(event, indent=2))
    print(event)
    # Parse the JSON string in the Payload field
    # payload_str = event['ResourceProperties']['Create']['parameters']['Payload']
    # payload = json.loads(payload_str)
    opensearch_endpoint = event["Endpoint"]
    index_name = event["IndexName"]
    print(opensearch_endpoint)
    opensearch_client = get_opensearch_client(opensearch_endpoint)

    try:
        if event["RequestType"] == "Create":
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
                if not opensearch_client.indices.exists(index=params["index"]):
                    logger.info(f"Creating index {params['index']}")
                    opensearch_client.indices.create(
                        index=params["index"], body=params["body"]
                    )
                    logger.info(f"Index {params['index']} creation initiated.")
                else:
                    logger.info(f"Index {params['index']} already exists")
                # Wait for the index to be available and ready
                wait_for_index(opensearch_client, params["index"])
                logger.info(f"Index {params['index']} is ready.")
            except Exception as e:
                logger.error(f"Error creating or waiting for index: {e}")
                raise e  # Re-raise to fail the custom resource

        elif event["RequestType"] == "Delete":
            try:
                opensearch_client.indices.delete(index=index_name)
            except Exception as e:
                logger.error(e)

    except NoCredentialsError:
        logger.error("Credentials not available.")
