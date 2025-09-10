import boto3
import time
import json

aoss = boto3.client("opensearchserverless")


def handler(event, context):
    print("Received event:", json.dumps(event))
    request_type = event["RequestType"]
    collection_name = event["ResourceProperties"]["CollectionName"]
    index_name = event["ResourceProperties"]["IndexName"]

    if request_type == "Delete":
        return {"PhysicalResourceId": f"{collection_name}/{index_name}", "Data": {"Status": "DELETED"}}

    # Poll until both collection + index become ACTIVE
    for _ in range(60):  # 10 minutes max
        # 1. Check collection
        coll_resp = aoss.batch_get_collection(names=[collection_name])
        coll = next((c for c in coll_resp.get("collectionDetails", []) if c["name"] == collection_name), None)
        if not coll or coll["status"] != "ACTIVE":
            print(f"Collection {collection_name} status={coll['status'] if coll else 'MISSING'}")
            time.sleep(10)
            continue

        # 2. Check index
        idx_resp = aoss.batch_get_index(names=[index_name], collectionName=collection_name)
        idx = next((i for i in idx_resp.get("indexDetails", []) if i["name"] == index_name), None)

        if idx and idx["status"] == "ACTIVE":
            print(f"Index {index_name} in {collection_name} is ACTIVE")
            return {"PhysicalResourceId": f"{collection_name}/{index_name}", "Data": {"Status": "READY"}}

        print(f"Index {index_name} status={idx['status'] if idx else 'MISSING'}")
        time.sleep(10)

    raise Exception(f"Collection {collection_name} / Index {index_name} not ready after timeout")
