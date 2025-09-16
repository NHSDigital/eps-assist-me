#!/usr/bin/env bash
set -e

if [ -z "${PULL_REQUEST_ID}" ]; then
    echo "What is the pull request id?"
    read -r PULL_REQUEST_ID
else
    read -r -p "Getting exports for pull request id ${PULL_REQUEST_ID}. Is this correct?" yn
    case $yn in
        [Yy]* ) ;;
        [Nn]* ) exit;;
        * ) exit;;
    esac
fi

CF_EXPORTS=$(aws cloudformation list-exports --region eu-west-2 --output json)

KB_DOCS_BUCKET_NAME=$(echo "$CF_EXPORTS" | \
    jq \
    --arg EXPORT_NAME "epsam-pr-${PULL_REQUEST_ID}:kbDocsBucket:Name" \
    -r '.Exports[] | select(.Name == $EXPORT_NAME) | .Value')

echo "Bucket ${KB_DOCS_BUCKET_NAME}"

aws s3 cp --recursive sample_docs/ "s3://${KB_DOCS_BUCKET_NAME}/"
