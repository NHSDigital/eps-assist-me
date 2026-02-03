import json
from app.slack.slack_events import _create_feedback_blocks


def test_feedback_button_payload_has_required_keys():
    """
    sanity check that feedback button payload includes the shortened keys
    expected by process_async_slack_action:
    - mt -> message_ts
    - ch -> channel_id
    """

    # setup
    response_text = "Here is an answer."
    citations = []
    feedback_data = {
        "channel": "C12345",
        "message_ts": "1700000000.000000",
        "thread_ts": "1699999999.000000",
        "ck": "thread#C12345#1699999999.000000",
    }

    # execute
    blocks = _create_feedback_blocks(response_text, citations, feedback_data)

    # locate the feedback actions block
    action_block = next(
        (b for b in blocks if b.get("type") == "actions" and b.get("block_id") == "feedback_block"),
        None,
    )
    assert action_block is not None, "feedback action block not found"

    # grab the yes button
    yes_button = next(
        (el for el in action_block["elements"] if el["action_id"] == "feedback_yes"),
        None,
    )
    assert yes_button is not None, "yes button not found"

    payload = json.loads(yes_button["value"])

    # these are expected to fail until wiring is complete
    assert "mt" in payload, f"missing 'mt' key, got: {payload.keys()}"
    assert payload["mt"] == "1700000000.000000"

    assert "ch" in payload, f"missing 'ch' key, got: {payload.keys()}"
    assert payload["ch"] == "C12345"

    # tt was already handled, but assert for safety
    assert "tt" in payload
    assert payload["tt"] == "1699999999.000000"
