#!/usr/bin/env bash

cat <<EOF > payload.json
{ 
  "currentTag": "$CURRENT_DEPLOYED_TAG",
  "targetTag": "$DEV_TAG",
  "repoName": "eps-assist-me",
  "targetEnvironment": "$ENV",
  "productName": "EPS Assist Me",
  "releaseNotesPageId": "$PAGE_ID",
  "releaseNotesPageTitle": "Current EPS Assist Me release notes - $ENV"
}
EOF
cat payload.json

function_arn=$(aws cloudformation list-exports --query "Exports[?Name=='release-notes:CreateReleaseNotesLambdaArn'].Value" --output text)
aws lambda invoke --function-name "${function_arn}" --cli-binary-format raw-in-base64-out --payload file://payload.json out.txt
cat out.txt
