import boto3
import time
from aws_lambda_powertools import Logger

# Structured logger (auto-captures request ID, cold start, etc.)
logger = Logger(service="opensearch-index-waiter")

aoss = boto3.client("opensearchserverless")


@logger.inject_lambda_context(log_event=True, clear_state=True)
def handler(event, context):
    request_type = event["RequestType"]
    collection_name = event["ResourceProperties"]["CollectionName"]
    index_name = event["ResourceProperties"]["IndexName"]

    if request_type == "Delete":
        logger.info("Delete event - no action required", extra={"collection": collection_name, "index": index_name})
        return {"PhysicalResourceId": f"{collection_name}/{index_name}", "Data": {"Status": "DELETED"}}

    # Poll until both collection + index become ACTIVE
    for attempt in range(60):  # up to ~10 minutes
        # 1. Check collection
        try:
            coll_resp = aoss.batch_get_collection(names=[collection_name])
            coll = next((c for c in coll_resp.get("collectionDetails", []) if c["name"] == collection_name), None)

            if not coll:
                logger.warning("Collection missing", extra={"collection": collection_name, "attempt": attempt})
                time.sleep(10)
                continue

            logger.info("Collection status check", extra={"collection": collection_name, "status": coll["status"]})
            if coll["status"] != "ACTIVE":
                time.sleep(10)
                continue

            # 2. Check index
            idx_resp = aoss.batch_get_index(names=[index_name], collectionName=collection_name)
            idx = next((i for i in idx_resp.get("indexDetails", []) if i["name"] == index_name), None)

            if not idx:
                logger.warning(
                    "Index missing", extra={"collection": collection_name, "index": index_name, "attempt": attempt}
                )
                time.sleep(10)
                continue

            logger.info(
                "Index status check",
                extra={"collection": collection_name, "index": index_name, "status": idx["status"]},
            )
            if idx["status"] == "ACTIVE":
                logger.info("Index is ready ✅", extra={"collection": collection_name, "index": index_name})
                return {"PhysicalResourceId": f"{collection_name}/{index_name}", "Data": {"Status": "READY"}}

            time.sleep(10)
        except Exception as exc:
            logger.error("Error creating or waiting for index", extra={"error": str(exc)})
            return {"PhysicalResourceId": f"{collection_name}/{index_name}", "Data": {"Status": "READY"}}

    logger.error("Timeout waiting for index readiness", extra={"collection": collection_name, "index": index_name})
    raise Exception(f"Collection {collection_name} / Index {index_name} not ready after timeout")
