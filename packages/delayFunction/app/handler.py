import json
import uuid
from time import sleep


def handler(event, context):
    wait_seconds = 0
    resource_id = str(uuid.uuid1())

    print(f"Received event: {json.dumps(event, default=str)}")

    try:
        if event["RequestType"] == "Create":
            wait_seconds = int(event["ResourceProperties"].get("WaitSeconds", 0))
            print(f"Waiting for {wait_seconds} seconds...")
            sleep(wait_seconds)
            print("Wait complete")

        return {
            "PhysicalResourceId": f"Waiter-{resource_id}",
            "Data": {"TimeWaited": wait_seconds, "Id": resource_id, "Status": "SUCCESS"},
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        raise
