from app.core.config import get_slack_bot_state_table


def get_state_information(key):
    table = get_slack_bot_state_table()
    return table.get_item(Key=key)


def store_state_information(item, condition=None):
    table = get_slack_bot_state_table()
    if condition:
        table.put_item(Item=item, ConditionExpression=condition)
    else:
        table.put_item(Item=item)


def update_state_information(key, update_expression, expression_attribute_values):
    table = get_slack_bot_state_table()
    table.update_item(
        Key=key, UpdateExpression=update_expression, ExpressionAttributeValues=expression_attribute_values
    )


def delete_state_information(pk, sk, condition):
    table = get_slack_bot_state_table()
    table.delete_item(
        Key={"pk": pk, "sk": sk},
        ConditionExpression=condition,
    )
