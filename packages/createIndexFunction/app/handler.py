import json
import time
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from app.config.config import AWS_REGION

logger = Logger(service="createIndexFunction")


def get_opensearch_client(endpoint):
    """Create an OpenSearch (AOSS) client using AWS credentials."""
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
    """Wait until the index exists in OpenSearch Serverless (AOSS)."""
    logger.info(f"Waiting for index '{index_name}' to be available in AOSS...")
    start = time.time()
    while True:
        try:
            if opensearch_client.indices.exists(index=index_name):
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
    """Creates the index (if not present) and waits until it's ready for use."""
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
                        "index": False,
                    },
                    "AMAZON_BEDROCK_TEXT_CHUNK": {
                        "type": "text",
                        "index": True,
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
    """Extract parameters from Lambda event."""
    if "ResourceProperties" in event:
        properties = event["ResourceProperties"]
        return {
            "endpoint": properties.get("Endpoint"),
            "index_name": properties.get("IndexName"),
            "request_type": event.get("RequestType"),
        }
    else:
        return {
            "endpoint": event.get("Endpoint"),
            "index_name": event.get("IndexName"),
            "request_type": event.get("RequestType"),
        }


@logger.inject_lambda_context
def handler(event: dict, context: LambdaContext) -> dict:
    """Entrypoint: create, update, or delete the OpenSearch index."""
    logger.info("Received event", extra={"event": event})

    try:
        if "Payload" in event:
            event = json.loads(event["Payload"])

        params = extract_parameters(event)
        endpoint = params["endpoint"]
        index_name = params["index_name"]
        request_type = params["request_type"]

        if not endpoint or not index_name or not request_type:
            raise ValueError("Missing required parameters: Endpoint, IndexName, or RequestType")

        client = get_opensearch_client(endpoint)

        if request_type in ["Create", "Update"]:
            create_and_wait_for_index(client, index_name)
            return {"PhysicalResourceId": f"index-{index_name}", "Status": "SUCCESS"}
        elif request_type == "Delete":
            try:
                if client.indices.exists(index=index_name):
                    client.indices.delete(index=index_name)
                    logger.info(f"Deleted index {index_name}")
            except Exception as e:
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
