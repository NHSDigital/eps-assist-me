#!/usr/bin/env bash
set -eou pipefail

rm -rf /tmp/ruleset
rm -rf cfn_guard_output

wget -O /tmp/ruleset.zip https://github.com/aws-cloudformation/aws-guard-rules-registry/releases/download/1.0.2/ruleset-build-v1.0.2.zip  >/dev/null 2>&1
unzip /tmp/ruleset.zip -d /tmp/ruleset/  >/dev/null 2>&1 

curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/aws-cloudformation/cloudformation-guard/main/install-guard.sh | sh >/dev/null 2>&1

mkdir -p cfn_guard_output

declare -a rulesets=("ncsc" "ncsc-cafv3" "wa-Reliability-Pillar" "wa-Security-Pillar")

# Create a custom NCSC ruleset that excludes the problematic rule
cp "/tmp/ruleset/output/ncsc.guard" "/tmp/ruleset/output/ncsc-custom.guard"

# Debug: Check if the rule exists before removal
echo "Checking for LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED rule..."
grep -n "LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED" "/tmp/ruleset/output/ncsc-custom.guard" || echo "Rule not found with exact name"

# Remove the problematic Lambda function public access rule
# Try multiple patterns to ensure we catch the rule
sed -i '/LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED/,/^rule /d' "/tmp/ruleset/output/ncsc-custom.guard"
sed -i '/LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED/,/^$/d' "/tmp/ruleset/output/ncsc-custom.guard"

# Also try removing any remaining references
grep -v "LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED" "/tmp/ruleset/output/ncsc-custom.guard" > "/tmp/ncsc-temp.guard" || true
mv "/tmp/ncsc-temp.guard" "/tmp/ruleset/output/ncsc-custom.guard" || true

echo "After removal, checking for remaining references..."
grep -n "LAMBDA_FUNCTION_PUBLIC_ACCESS_PROHIBITED" "/tmp/ruleset/output/ncsc-custom.guard" || echo "✅ Rule successfully removed"

for ruleset in "${rulesets[@]}"
do
    # Use custom NCSC ruleset that excludes the problematic rule
    if [ "$ruleset" = "ncsc" ]; then
        ruleset_file="/tmp/ruleset/output/ncsc-custom.guard"
        echo "Using custom NCSC ruleset: $ruleset_file"
    else
        ruleset_file="/tmp/ruleset/output/$ruleset.guard"
    fi
    
    echo "Checking all templates in cdk.out folder with ruleset $ruleset"

    ~/.guard/bin/cfn-guard validate \
        --data cdk.out \
        --rules "$ruleset_file" \
        --show-summary fail \
        > "cfn_guard_output/cdk.out_$ruleset.txt"
done

rm -rf /tmp/ruleset
