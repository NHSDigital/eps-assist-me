import sys
from unittest.mock import Mock, patch


@patch("app.services.app.get_app")
@patch("slack_bolt.adapter.aws_lambda.SlackRequestHandler")
def test_handler_normal_event(
    mock_handler_class: Mock,
    mock_get_app: Mock,
    mock_slack_app: Mock,
    mock_env: Mock,
    mock_get_parameter: Mock,
    lambda_context: Mock,
):
    """Test Lambda handler function for normal Slack events"""
    # set up mocks
    mock_get_app.return_value = mock_slack_app
    mock_handler = Mock()
    mock_handler_class.return_value = mock_handler
    mock_handler.handle.return_value = {"statusCode": 200}

    # delete and import module to test
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # perform operation
    event = {"body": "test event"}
    result = handler(event, lambda_context)

    # assertions
    mock_handler.handle.assert_called_once_with(event=event, context=lambda_context)
    assert result["statusCode"] == 200


@patch("app.services.app.get_app")
@patch("app.slack.slack_events.process_pull_request_slack_event")
def test_handler_pull_request_event_processing(
    mock_process_pull_request_slack_event: Mock,
    mock_get_app: Mock,
    mock_get_parameter: Mock,
    mock_slack_app: Mock,
    mock_env: Mock,
    lambda_context: Mock,
):
    """Test Lambda handler function for pull request processing"""
    # set up mocks
    mock_get_app.return_value = mock_slack_app

    # delete and import module to test
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # perform operation
    event = {"pull_request_event": True, "slack_event": {"body": "test event"}}
    handler(event, lambda_context)

    # assertions
    mock_process_pull_request_slack_event.assert_called_once_with(slack_event_data={"body": "test event"})


@patch("app.services.app.get_app")
@patch("app.slack.slack_events.process_pull_request_slack_event")
def test_handler_pull_request_event_processing_missing_slack_event(
    mock_process_pull_request_slack_event: Mock,
    mock_get_app: Mock,
    mock_slack_app: Mock,
    mock_env: Mock,
    mock_get_parameter: Mock,
    lambda_context: Mock,
):
    """Test Lambda handler function for async processing without slack_event data"""
    # set up mocks
    mock_get_app.return_value = mock_slack_app

    # delete and import module to test
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # perform operation
    # Test async processing without slack_event - should return 400
    event = {"pull_request_event": True}  # Missing slack_event
    result = handler(event, lambda_context)

    # assertions
    # Check that result is a dict with statusCode
    assert isinstance(result, dict)
    assert "statusCode" in result
    assert result["statusCode"] == 400
    mock_process_pull_request_slack_event.assert_not_called()


@patch("app.services.app.get_app")
@patch("app.slack.slack_events.process_pull_request_slack_action")
def test_handler_pull_request_action_processing(
    mock_process_pull_request_slack_action: Mock,
    mock_get_app: Mock,
    mock_get_parameter: Mock,
    mock_slack_app: Mock,
    mock_env: Mock,
    lambda_context: Mock,
):
    """Test Lambda handler function for pull request processing"""
    # set up mocks
    mock_get_app.return_value = mock_slack_app

    # delete and import module to test
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # perform operation
    event = {"pull_request_action": True, "slack_body": {"body": "test event"}}
    handler(event, lambda_context)

    # assertions
    mock_process_pull_request_slack_action.assert_called_once_with(slack_body_data={"body": "test event"})


@patch("app.services.app.get_app")
@patch("app.slack.slack_events.process_pull_request_slack_action")
def test_handler_pull_request_action_missing_slack_event(
    mock_process_pull_request_slack_action: Mock,
    mock_get_app: Mock,
    mock_slack_app: Mock,
    mock_env: Mock,
    mock_get_parameter: Mock,
    lambda_context: Mock,
):
    """Test Lambda handler function for async processing without slack_event data"""
    # set up mocks
    mock_get_app.return_value = mock_slack_app

    # delete and import module to test
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # perform operation
    # Test async processing without slack_event - should return 400
    event = {"pull_request_action": True}  # Missing slack_event
    result = handler(event, lambda_context)

    # assertions
    # Check that result is a dict with statusCode
    assert isinstance(result, dict)
    assert "statusCode" in result
    assert result["statusCode"] == 400
    mock_process_pull_request_slack_action.assert_not_called()


@patch("app.services.app.get_app")
@patch("app.slack.slack_events.process_pull_request_slack_command")
def test_handler_pull_request_command_processing(
    mock_process_pull_request_slack_command: Mock,
    mock_get_app: Mock,
    mock_get_parameter: Mock,
    mock_slack_app: Mock,
    mock_env: Mock,
    lambda_context: Mock,
):
    """Test Lambda handler function for pull request processing"""
    # set up mocks
    mock_get_app.return_value = mock_slack_app

    # delete and import module to test
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # perform operation
    event = {"pull_request_command": True, "slack_event": {"body": "test command"}}
    handler(event, lambda_context)

    # assertions
    mock_process_pull_request_slack_command.assert_called_once_with(slack_command_data={"body": "test command"})


@patch("app.services.app.get_app")
@patch("app.slack.slack_events.process_pull_request_slack_command")
def test_handler_pull_request_command_processing_missing_slack_command(
    mock_process_pull_request_slack_command: Mock,
    mock_get_app: Mock,
    mock_slack_app: Mock,
    mock_env: Mock,
    mock_get_parameter: Mock,
    lambda_context: Mock,
):
    """Test Lambda handler function for async processing without slack_command data"""
    # set up mocks
    mock_get_app.return_value = mock_slack_app

    # delete and import module to test
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # perform operation
    # Test async processing without slack_event - should return 400
    event = {"pull_request_command": True}  # Missing slack_command
    result = handler(event, lambda_context)

    # assertions
    # Check that result is a dict with statusCode
    assert isinstance(result, dict)
    assert "statusCode" in result
    assert result["statusCode"] == 400
    mock_process_pull_request_slack_command.assert_not_called()


@patch("app.services.ai_processor.process_ai_query")
def test_handler_direct_invocation(
    mock_process_ai_query: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
    lambda_context: Mock,
):
    """main handler routes direct invocation to bypass slack entirely"""
    # mock ai response - same structure as slack handlers expect
    mock_process_ai_query.return_value = {
        "text": "AI response",
        "session_id": "session-123",
        "citations": [],
        "kb_response": {"sessionId": "session-123"},
    }

    # fresh import: avoid cached modules affecting test isolation
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handler

    # direct invocation bypasses slack webhook processing
    event = {
        "invocation_type": "direct",
        "query": "How do I authenticate with EPS API?",
        "session_id": "existing-session",
    }
    result = handler(event, lambda_context)

    # verify direct invocation produces expected api response
    assert result["statusCode"] == 200
    assert result["response"]["text"] == "AI response"
    assert result["response"]["session_id"] == "session-123"
    assert "timestamp" in result["response"]


@patch("app.services.ai_processor.process_ai_query")
def test_handle_direct_invocation_success(
    mock_process_ai_query: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
    lambda_context: Mock,
):
    """successful ai query processing via direct handler"""
    # realistic ai response with citations
    mock_process_ai_query.return_value = {
        "text": "Authentication requires OAuth 2.0...",
        "session_id": "new-session-456",
        "citations": [{"title": "EPS API Guide", "uri": "https://example.com"}],
        "kb_response": {"sessionId": "new-session-456"},
    }

    # fresh import for test isolation
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handle_direct_invocation

    # minimal direct invocation event structure
    event = {"invocation_type": "direct", "query": "How do I authenticate with EPS API?"}
    result = handle_direct_invocation(event, lambda_context)

    # verify response structure and ai service integration
    assert result["statusCode"] == 200
    assert result["response"]["text"] == "Authentication requires OAuth 2.0..."
    assert result["response"]["session_id"] == "new-session-456"
    assert len(result["response"]["citations"]) == 1
    assert "timestamp" in result["response"]
    mock_process_ai_query.assert_called_once_with("How do I authenticate with EPS API?", None)


def test_handle_direct_invocation_missing_query(
    mock_get_parameter: Mock,
    mock_env: Mock,
    lambda_context: Mock,
):
    """input validation: missing query returns 400 error"""
    # fresh import for test isolation
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handle_direct_invocation

    # invalid event: no query field provided
    event = {"invocation_type": "direct"}
    result = handle_direct_invocation(event, lambda_context)

    # verify validation error with proper http status
    assert result["statusCode"] == 400
    assert "Missing required field: query" in result["response"]["error"]
    assert "timestamp" in result["response"]


@patch("app.services.ai_processor.process_ai_query")
def test_handle_direct_invocation_processing_error(
    mock_process_ai_query: Mock,
    mock_get_parameter: Mock,
    mock_env: Mock,
    lambda_context: Mock,
):
    """ai service failure: graceful error handling without exposing internals"""
    # simulate ai service failure
    mock_process_ai_query.side_effect = Exception("AI service unavailable")

    # fresh import for test isolation
    if "app.handler" in sys.modules:
        del sys.modules["app.handler"]
    from app.handler import handle_direct_invocation

    # valid request but ai processing fails
    event = {"invocation_type": "direct", "query": "How do I authenticate with EPS API?"}
    result = handle_direct_invocation(event, lambda_context)

    # verify 500 error with generic message - no internal details leaked
    assert result["statusCode"] == 500
    assert result["response"]["error"] == "Internal server error"
    assert "timestamp" in result["response"]
