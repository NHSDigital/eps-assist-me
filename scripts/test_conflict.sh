#!/usr/bin/env bash
set -e

REGION="eu-west-2"
FUNCTION_NAME="epsam-FunctionsSlackBotLambdaepsamSlackBotFunction-oJmZsZb4CmPQ"

# 1. Log into AWS
echo -e "\nLogging into AWS SSO..."

# FIX (SC2181): Check the command directly instead of using $?
if ! aws login; then
    echo -e "\nWarning: AWS login may have failed or you are using standard IAM keys. Continuing anyway..."
fi

# 2. Ask for Channel ID
echo ""
# FIX (SC2162): Added -r to prevent mangling of backslashes
read -r -p "Enter the Slack Channel ID (e.g., C12345678): " CHANNEL_ID

echo -e "\nPreparing payloads with current time..."

# Generate Unix Epoch time and stagger slightly
NOW=$(date +%s)
THREAD_TS="${NOW}.000"
MENTION_TS="${NOW}.050"
MESSAGE_TS="${NOW}.100"

# Generate random GUIDs
if command -v uuidgen &> /dev/null; then
    MENTION_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
    MESSAGE_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
else
    MENTION_UUID=$(cat /proc/sys/kernel/random/uuid)
    MESSAGE_UUID=$(cat /proc/sys/kernel/random/uuid)
fi

# Create temporary files
MENTION_PAYLOAD_FILE=$(mktemp)
MESSAGE_PAYLOAD_FILE=$(mktemp)
MENTION_OUT_FILE=$(mktemp)
MESSAGE_OUT_FILE=$(mktemp)

# Build JSON Payloads
cat <<EOF > "$MENTION_PAYLOAD_FILE"
{
  "pull_request_event": true,
  "slack_event": {
    "event_id": "$MENTION_UUID",
    "event": {
      "type": "app_mention",
      "user": "U09N5F3SH5G",
      "text": "<@bot> What is the first step?",
      "channel": "$CHANNEL_ID",
      "ts": "$MENTION_TS",
      "thread_ts": "$THREAD_TS",
      "event_ts": "$THREAD_TS",
      "channel_type": "channel"
    }
  }
}
EOF

cat <<EOF > "$MESSAGE_PAYLOAD_FILE"
{
  "pull_request_event": true,
  "slack_event": {
    "event_id": "$MESSAGE_UUID",
    "event": {
      "type": "message",
      "user": "U09N5F3SH5G",
      "text": "<@bot> What is the first step?",
      "channel": "$CHANNEL_ID",
      "ts": "$MESSAGE_TS",
      "thread_ts": "$THREAD_TS",
      "event_ts": "$THREAD_TS",
      "channel_type": "channel"
    }
  }
}
EOF

echo -e "Triggering events concurrently...\n"

# Function to run the AWS CLI lambda invoke command
invoke_lambda() {
    local payload_file=$1
    local out_file=$2
    local label=$3

    aws lambda invoke \
      --function-name "$FUNCTION_NAME" \
      --region "$REGION" \
      --profile "${AWS_PROFILE:-default}" \
      --cli-binary-format raw-in-base64-out \
      --invocation-type RequestResponse \
      --payload "file://$payload_file" \
      "$out_file"

    if [ -s "$out_file" ]; then
        echo "$label Result: $(cat "$out_file")"
    else
        echo "$label Result: Error - Output file missing or empty."
    fi
}

# 3. Send both requests at the same time using background jobs (&)
invoke_lambda "$MENTION_PAYLOAD_FILE" "$MENTION_OUT_FILE" "Mention" &
PID_MENTION=$!

invoke_lambda "$MESSAGE_PAYLOAD_FILE" "$MESSAGE_OUT_FILE" "Message" &
PID_MESSAGE=$!

# Wait for both background processes to finish
wait "$PID_MENTION"
wait "$PID_MESSAGE"

# Clean up temporary files
rm -f "$MENTION_PAYLOAD_FILE" "$MESSAGE_PAYLOAD_FILE" "$MENTION_OUT_FILE" "$MESSAGE_OUT_FILE"

echo -e "\nExecution complete and temporary files cleaned up."
