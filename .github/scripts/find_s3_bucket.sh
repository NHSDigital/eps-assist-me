#!/usr/bin/env bash

# Arguments
PARTIAL_NAME=$1

if [ -z "$PARTIAL_NAME" ]; then
  echo "Error: No partial bucket name provided."
  exit 1
fi

echo "Searching for bucket containing: $PARTIAL_NAME..."

# List buckets and filter using JMESPath
# We use 'tail -n 1' or 'awk' to ensure we only get one result if multiple match
BUCKET_NAME=$(aws cloudformation list-exports --query "Exports[?Name=='epsam:kbDocsBucket:Name'].Value" --output text)

if [ -z "$BUCKET_NAME" ] || [ "$BUCKET_NAME" == "None" ]; then
  echo "Error: No bucket found matching '$PARTIAL_NAME'"
  exit 1
fi

echo "Success: Found bucket '$BUCKET_NAME'"

# This special syntax tells GitHub Actions to set an output variable
echo "BUCKET_NAME=$BUCKET_NAME" >> "$GITHUB_OUTPUT"
