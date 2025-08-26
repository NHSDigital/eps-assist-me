import json
import sys
from unittest.mock import Mock, patch


@patch("slack_bolt.App")
@patch("aws_lambda_powertools.utilities.parameters.get_parameter")
@patch("boto3.resource")
@patch("boto3.client")
def test_get_bedrock_knowledgebase_response(
    mock_boto_client, mock_boto_resource, mock_get_parameter, mock_app, mock_env
):
    """Test Bedrock knowledge base integration"""
    mock_get_parameter.side_effect = [
        json.dumps({"token": "test-token"}),
        json.dumps({"secret": "test-secret"}),
    ]
    mock_boto_resource.return_value.Table.return_value = Mock()

    mock_client = Mock()
    mock_boto_client.return_value = mock_client
    mock_client.retrieve_and_generate.return_value = {"output": {"text": "bedrock response"}}

    if "app.slack.slack_events" in sys.modules:
        del sys.modules["app.slack.slack_events"]

    from app.slack.slack_events import query_bedrock

    result = query_bedrock("test query")

    mock_boto_client.assert_called_once_with(service_name="bedrock-agent-runtime", region_name="eu-west-2")
    mock_client.retrieve_and_generate.assert_called_once()
    assert result["output"]["text"] == "bedrock response"
