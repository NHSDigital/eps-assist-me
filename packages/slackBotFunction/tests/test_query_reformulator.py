from unittest.mock import patch, MagicMock
import json
from query_reformulator import reformulate_query


@patch("query_reformulator.boto3.client")
@patch.dict(
    "os.environ",
    {
        "AWS_REGION": "eu-west-2",
        "QUERY_REFORMULATION_PROMPT_ARN": "arn:aws:bedrock:eu-west-2:123456789012:prompt/test-prompt",
    },
)
def test_reformulate_query_success(mock_boto_client):
    # Mock Bedrock response
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client

    mock_response = {"body": MagicMock()}
    mock_response["body"].read.return_value = json.dumps(
        {"content": [{"text": "NHS EPS Electronic Prescription Service API FHIR prescription dispensing"}]}
    ).encode()

    mock_client.invoke_model.return_value = mock_response

    result = reformulate_query("How do I use EPS?")

    assert result == "NHS EPS Electronic Prescription Service API FHIR prescription dispensing"
    mock_client.invoke_model.assert_called_once()


@patch("query_reformulator.boto3.client")
@patch.dict(
    "os.environ",
    {
        "AWS_REGION": "eu-west-2",
        "QUERY_REFORMULATION_PROMPT_ARN": "arn:aws:bedrock:eu-west-2:123456789012:prompt/test-prompt",
    },
)
def test_reformulate_query_fallback_on_error(mock_boto_client):
    # Mock Bedrock client to raise exception
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    mock_client.invoke_model.side_effect = Exception("Bedrock error")

    original_query = "How do I use EPS?"
    result = reformulate_query(original_query)

    # Should fallback to original query on error
    assert result == original_query
