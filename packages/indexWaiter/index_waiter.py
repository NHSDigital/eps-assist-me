import boto3
import time
from aws_lambda_powertools import Logger
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

# Structured logger (auto-captures request ID, cold start, etc.)
logger = Logger(service="opensearch-index-waiter")

aoss = boto3.client("opensearchserverless")
AWS_REGION = "eu-west-2"


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


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event, context):
    request_type = event["RequestType"]
    endpoint = event["ResourceProperties"]["Endpoint"]
    index_name = event["ResourceProperties"]["IndexName"]

    if request_type == "Delete":
        logger.info("Delete event - no action required", extra={"endpoint": endpoint, "index": index_name})
        return {"PhysicalResourceId": f"index-{index_name}", "Data": {"Status": "DELETED"}}

    client = get_opensearch_client(endpoint)
    if not wait_for_index_aoss(client, index_name):
        raise RuntimeError(f"Index {index_name} failed to appear in time")
    return {
        "PhysicalResourceId": event.get("PhysicalResourceId", f"index-{index_name}"),
        "Status": "SUCCESS",
    }
