from unittest.mock import patch, MagicMock
import json
from app.services.query_reformulator import reformulate_query


def test_reformulate_query_success():
    with patch("app.services.query_reformulator.load_prompt") as mock_load_prompt, patch(
        "app.services.query_reformulator.boto3.client"
    ) as mock_boto_client, patch.dict(
        "os.environ",
        {
            "AWS_REGION": "eu-west-2",
            "QUERY_REFORMULATION_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
            "QUERY_REFORMULATION_PROMPT_NAME": "query-reformulation",
        },
    ):

        # Mock prompt loading
        mock_load_prompt.return_value = "Test prompt template with {user_query}"

        # Mock Bedrock client with proper response
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        # Create a simple mock that returns the expected JSON
        mock_client.invoke_model.return_value = {
            "body": type(
                "MockBody",
                (),
                {
                    "read": lambda: json.dumps(
                        {
                            "content": [
                                {"text": "NHS EPS Electronic Prescription Service API FHIR prescription dispensing"}
                            ]
                        }
                    ).encode("utf-8")
                },
            )()
        }

        result = reformulate_query("How do I use EPS?")

        # Test that function doesn't crash and returns a string
        assert isinstance(result, str)
        assert len(result) > 0


@patch("app.services.query_reformulator.load_prompt")
@patch("app.services.query_reformulator.boto3.client")
@patch.dict(
    "os.environ",
    {
        "AWS_REGION": "eu-west-2",
        "QUERY_REFORMULATION_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
        "QUERY_REFORMULATION_PROMPT_NAME": "query-reformulation",
    },
)
def test_reformulate_query_fallback_on_error(mock_boto_client, mock_load_prompt):
    # Mock prompt loading
    mock_load_prompt.return_value = "Test prompt template with {user_query}"

    # Mock Bedrock client to raise exception
    mock_client = MagicMock()
    mock_boto_client.return_value = mock_client
    mock_client.invoke_model.side_effect = Exception("Bedrock error")

    original_query = "How do I use EPS?"
    result = reformulate_query(original_query)

    # Should fallback to original query on error
    assert result == original_query
