from app.core.config import get_logger, get_slack_bot_state_table
from time import time

logger = get_logger()


def get_state_information(key):
    start_time = time()
    table = get_slack_bot_state_table()
    is_success = True
    try:
        results = table.get_item(Key=key)
    except Exception as e:
        is_success = False
        raise e
    finally:
        end_time = time()
        logger.debug(
            "get_state_information duration",
            extra={
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "is_success": is_success,
            },
        )
    return results


def store_state_information(item, condition=None):
    start_time = time()
    table = get_slack_bot_state_table()
    is_success = True
    try:
        if condition:
            table.put_item(Item=item, ConditionExpression=condition)
        else:
            table.put_item(Item=item)
    except Exception as e:
        is_success = False
        raise e
    finally:
        end_time = time()
        logger.debug(
            "store_state_information duration",
            extra={
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "is_success": is_success,
            },
        )


def update_state_information(key, update_expression, expression_attribute_values):
    start_time = time()
    table = get_slack_bot_state_table()
    is_success = True
    try:
        table.update_item(
            Key=key, UpdateExpression=update_expression, ExpressionAttributeValues=expression_attribute_values
        )
    except Exception as e:
        is_success = False
        raise e
    finally:
        end_time = time()
        logger.debug(
            "update_state_information duration",
            extra={
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "is_success": is_success,
            },
        )


def delete_state_information(pk, sk, condition):
    start_time = time()
    table = get_slack_bot_state_table()
    is_success = True
    try:
        table.delete_item(
            Key={"pk": pk, "sk": sk},
            ConditionExpression=condition,
        )
    except Exception as e:
        is_success = False
        raise e
    finally:
        end_time = time()
        logger.debug(
            "delete_state_information duration",
            extra={
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "is_success": is_success,
            },
        )
