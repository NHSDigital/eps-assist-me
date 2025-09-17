#!/usr/bin/env bash
set -e

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo "Script directory: $CURRENT_DIR"

mkdir -p .local_config
FIX_SCRIPT="${CURRENT_DIR}/../.github/scripts/fix_cdk_json.sh"
EPSAM_CONFIG=".local_config/epsam_app.config.json"
EPSAM_LOG=".local_config/epsam_app.log"

if [ -z "${PULL_REQUEST_ID}" ]; then
    echo "What is the pull request id? "
    read -r PULL_REQUEST_ID
else
    read -r -p "Getting exports for pull request id ${PULL_REQUEST_ID}. Is this correct? " yn
    case $yn in
        [Yy]* ) ;;
        [Nn]* ) exit;;
        * ) exit;;
    esac
fi

STACK_NAME=epsam-pr-$PULL_REQUEST_ID

echo "Getting exports from stack ${STACK_NAME}"

CF_LONDON_EXPORTS=$(aws cloudformation list-exports --region eu-west-2 --output json)


# vars needed for cdk

COMMIT_ID=$(echo "$CF_LONDON_EXPORTS" | \
    jq \
    --arg EXPORT_NAME "${STACK_NAME}:local:COMMIT-ID" \
    -r '.Exports[] | select(.Name == $EXPORT_NAME) | .Value')
VERSION_NUMBER=$(echo "$CF_LONDON_EXPORTS" | \
    jq \
    --arg EXPORT_NAME "${STACK_NAME}:local:VERSION-NUMBER" \
    -r '.Exports[] | select(.Name == $EXPORT_NAME) | .Value')
SLACK_BOT_TOKEN=$(echo "$CF_LONDON_EXPORTS" | \
    jq \
    --arg EXPORT_NAME "${STACK_NAME}:local:slackBotToken" \
    -r '.Exports[] | select(.Name == $EXPORT_NAME) | .Value')
SLACK_SIGNING_SECRET=$(echo "$CF_LONDON_EXPORTS" | \
    jq \
    --arg EXPORT_NAME "${STACK_NAME}:local:slackSigningSecret" \
    -r '.Exports[] | select(.Name == $EXPORT_NAME) | .Value')
LOG_RETENTION_IN_DAYS=30
LOG_LEVEL=debug

# export all the vars so they can be picked up by external programs
export STACK_NAME
export COMMIT_ID
export VERSION_NUMBER
export SLACK_BOT_TOKEN
export SLACK_SIGNING_SECRET
export LOG_RETENTION_IN_DAYS
export LOG_LEVEL


echo "Generating config for ${EPSAM_CONFIG}"
"$FIX_SCRIPT" "$EPSAM_CONFIG"

echo "Installing dependencies locally"
mkdir -p .dependencies
poetry export --without-hashes --format=requirements.txt --with slackBotFunction > .dependencies/requirements_slackBotFunction
poetry export --without-hashes --format=requirements.txt --with syncKnowledgeBaseFunction > .dependencies/requirements_syncKnowledgeBaseFunction
pip3 install -r .dependencies/requirements_slackBotFunction -t .dependencies/slackBotFunction/python
pip3 install -r .dependencies/requirements_syncKnowledgeBaseFunction -t .dependencies/syncKnowledgeBaseFunction/python

sync_epsam_app() {
    echo "Starting sync epsam CDK app"
    echo "Stateful CDK app log file at ${EPSAM_LOG}"
    CONFIG_FILE_NAME="${EPSAM_CONFIG}" npx cdk deploy \
        --app "npx ts-node --prefer-ts-exts packages/cdk/bin/EpsAssistMeApp.ts" \
        --watch \
        --all \
        --ci true \
        --require-approval never \
        --output .local_config/epsam_app.out/ \
        > $EPSAM_LOG 2>&1
}


(trap 'kill 0' SIGINT; sync_epsam_app)
