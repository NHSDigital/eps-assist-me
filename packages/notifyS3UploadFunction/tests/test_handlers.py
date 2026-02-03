import json
import sys


def test_handler_successful_processing(mock_env, mock_get_parameter, mock_web_client, lambda_context):
    """Test successful processing of S3 upload events"""
    # Mock Slack client responses
    mock_web_client.auth_test.return_value = {"user_id": "bot-user"}
    mock_web_client.conversations_list.return_value = [{"channels": [{"id": "C123"}, {"id": "C456"}]}]
    mock_web_client.chat_postMessage.return_value = None

    # Import after patching
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Test event with S3 records
    event = {
        "Records": [
            {
                "body": json.dumps(
                    {
                        "Records": [
                            {"s3": {"bucket": {"name": "pr-123"}, "object": {"key": "file1.pdf"}}},
                            {"s3": {"bucket": {"name": "pr-456"}, "object": {"key": "folder/file2.txt"}}},
                        ]
                    }
                )
            }
        ]
    }

    result = handler(event, lambda_context)

    # Assertions
    assert result["status"] == "success"
    assert result["processed_files"] == 2
    assert result["channels_notified"] == 2

    # Verify Slack API calls
    mock_web_client.auth_test.assert_called_once()
    mock_web_client.conversations_list.assert_called_once_with(types=["private_channel"], limit=1000)
    assert mock_web_client.chat_postMessage.call_count == 2


def test_handler_no_files(mock_env, mock_get_parameter, mock_web_client, lambda_context):
    """Test handler with no valid S3 records"""
    # Mock Slack client
    mock_web_client.auth_test.return_value = {"user_id": "bot-user"}

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Event with empty records
    event = {"Records": []}

    result = handler(event, lambda_context)

    assert result["status"] == "skipped"
    assert result["processed_files"] == 0
    assert result["channels_notified"] == 0

    # Should not attempt to post messages
    mock_web_client.chat_postMessage.assert_not_called()


def test_handler_pr_branch(mock_env, mock_get_parameter, mock_web_client, lambda_context):
    """Test skips processing of S3 upload events when bucket name indicates a PR branch"""
    # Mock Slack client responses
    mock_web_client.auth_test.return_value = {"user_id": "bot-user"}
    mock_web_client.conversations_list.return_value = [{"channels": [{"id": "C123"}, {"id": "C456"}]}]
    mock_web_client.chat_postMessage.return_value = None

    # Import after patching
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Test event with S3 records
    event = {
        "Records": [
            {
                "body": json.dumps(
                    {
                        "Records": [
                            {"s3": {"bucket": {"name": "epsam-pr-123"}, "object": {"key": "file1.pdf"}}},
                            {"s3": {"bucket": {"name": "epsam-pr-456"}, "object": {"key": "folder/file2.txt"}}},
                        ]
                    }
                )
            }
        ]
    }

    result = handler(event, lambda_context)

    # Assertions
    assert result["status"] == "skipped"
    assert result["processed_files"] == 0
    assert result["channels_notified"] == 0

    # Verify Slack API calls
    mock_web_client.conversations_list.assert_not_called()


def test_handler_parsing_error(mock_env, mock_get_parameter, mock_web_client, lambda_context):
    """Test handler with malformed S3 event records"""
    # Mock Slack client
    mock_web_client.auth_test.return_value = {"user_id": "bot-user"}
    mock_web_client.conversations_list.return_value = [{"channels": [{"id": "C123"}]}]
    mock_web_client.chat_postMessage.return_value = None

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Event with invalid JSON in body
    event = {
        "Records": [
            {"body": "invalid json"},
            {
                "body": json.dumps(
                    {"Records": [{"s3": {"bucket": {"name": "test"}, "object": {"key": "folder/file1.pdf"}}}]}
                )
            },
        ]
    }

    result = handler(event, lambda_context)

    # Should process the valid record
    assert result["status"] == "success"
    assert result["processed_files"] == 1
    assert result["channels_notified"] == 1


def test_handler_deduplication(mock_env, mock_get_parameter, mock_web_client, lambda_context):
    """Test that duplicate files are deduplicated"""
    # Mock Slack client
    mock_web_client.auth_test.return_value = {"user_id": "bot-user"}
    mock_web_client.conversations_list.return_value = [{"channels": [{"id": "C123"}]}]
    mock_web_client.chat_postMessage.return_value = None

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Event with duplicate files
    event = {
        "Records": [
            {
                "body": json.dumps(
                    {
                        "Records": [
                            {"s3": {"bucket": {"name": "pr-123"}, "object": {"key": "folder/file1.pdf"}}},
                            {"s3": {"bucket": {"name": "pr-123"}, "object": {"key": "folder/file1.pdf"}}},  # duplicate
                            {"s3": {"bucket": {"name": "pr-511"}, "object": {"key": "folder/file2.txt"}}},
                        ]
                    }
                )
            }
        ]
    }

    result = handler(event, lambda_context)

    # Should deduplicate to 2 unique files
    assert result["status"] == "success"
    assert result["processed_files"] == 2
    assert result["channels_notified"] == 1


def test_handler_posting_failure(mock_env, mock_get_parameter, mock_web_client, lambda_context):
    """Test handling of posting failures to some channels"""
    from slack_sdk.errors import SlackApiError

    # Mock Slack client
    mock_web_client.auth_test.return_value = {"user_id": "bot-user"}
    mock_web_client.conversations_list.return_value = [{"channels": [{"id": "C123"}, {"id": "C456"}]}]
    # First call succeeds, second fails
    mock_web_client.chat_postMessage.side_effect = [None, SlackApiError("error", {"error": "channel_not_found"})]

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    event = {
        "Records": [
            {
                "body": json.dumps(
                    {"Records": [{"s3": {"bucket": {"name": "pr-123"}, "object": {"key": "folder/file1.pdf"}}}]}
                )
            }
        ]
    }

    result = handler(event, lambda_context)

    # Should still succeed but only notify 1 channel
    assert result["status"] == "success"
    assert result["processed_files"] == 1
    assert result["channels_notified"] == 1

    assert mock_web_client.chat_postMessage.call_count == 2


def test_handler_no_channels(mock_env, mock_get_parameter, mock_web_client, lambda_context):
    """Test when bot is not a member of any channels"""
    # Mock Slack client
    mock_web_client.auth_test.return_value = {"user_id": "bot-user"}
    mock_web_client.conversations_list.return_value = [{"channels": []}]  # No channels

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    event = {
        "Records": [
            {
                "body": json.dumps(
                    {"Records": [{"s3": {"bucket": {"name": "test"}, "object": {"key": "folder/file1.pdf"}}}]}
                )
            }
        ]
    }

    result = handler(event, lambda_context)

    assert result["status"] == "failed"
    assert result["processed_files"] == 1
    assert result["channels_notified"] == 0

    mock_web_client.chat_postMessage.assert_not_called()


def test_handler_many_files_truncation(mock_env, mock_get_parameter, mock_web_client, lambda_context):
    """Test message truncation when there are many files"""
    # Mock Slack client
    mock_web_client.auth_test.return_value = {"user_id": "bot-user"}
    mock_web_client.conversations_list.return_value = [{"channels": [{"id": "C123"}]}]
    mock_web_client.chat_postMessage.return_value = None

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # Create 15 files
    files = [{"s3": {"bucket": {"name": "pr-123"}, "object": {"key": f"folder/file{i}.pdf"}}} for i in range(15)]
    event = {"Records": [{"body": json.dumps({"Records": files})}]}

    result = handler(event, lambda_context)

    assert result["status"] == "success"
    assert result["processed_files"] == 15
    assert result["channels_notified"] == 1

    # Check the message content
    call_args = mock_web_client.chat_postMessage.call_args
    blocks = call_args[1]["blocks"]
    text = blocks[0]["text"]["text"]
    assert "15 New Document(s) Uploaded" in text
    assert "...and 5 more." in text  # 10 displayed + 5 more


def test_handler_conversations_list_error(mock_env, mock_get_parameter, mock_web_client, lambda_context):
    """Test handling of error when fetching channels"""
    # Mock Slack client to raise error on conversations_list
    mock_web_client.auth_test.return_value = {"user_id": "bot-user"}
    mock_web_client.conversations_list.side_effect = Exception("Network error")

    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    event = {
        "Records": [
            {
                "body": json.dumps(
                    {"Records": [{"s3": {"bucket": {"name": "pr-123"}, "object": {"key": "folder/file1.pdf"}}}]}
                )
            }
        ]
    }

    result = handler(event, lambda_context)

    # Should return false since no channels found
    assert result["status"] == "failed"
    assert result["processed_files"] == 1
    assert result["channels_notified"] == 0

    mock_web_client.chat_postMessage.assert_not_called()
