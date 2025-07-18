guard-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
	fi

.PHONY: install build test publish release clean

install: install-python install-hooks install-node

install-python:
	poetry install

install-hooks: install-python
	poetry run pre-commit install --install-hooks --overwrite

install-node:
	npm ci

compile-node:
	npx tsc --build tsconfig.build.json

pre-commit: git-secrets-docker-setup
	poetry run pre-commit run --all-files

git-secrets-docker-setup:
	export LOCAL_WORKSPACE_FOLDER=$(pwd)
	docker build -f https://raw.githubusercontent.com/NHSDigital/eps-workflow-quality-checks/refs/tags/v4.0.4/dockerfiles/nhsd-git-secrets.dockerfile -t git-secrets .

download-get-secrets-layer:
	mkdir -p packages/getSecretLayer/lib
	curl -LJ https://github.com/NHSDigital/electronic-prescription-service-get-secrets/releases/download/$$(curl -s "https://api.github.com/repos/NHSDigital/electronic-prescription-service-get-secrets/releases/latest" | jq -r .tag_name)/get-secrets-layer.zip -o packages/getSecretLayer/lib/get-secrets-layer.zip

lint: lint-githubactions lint-githubaction-scripts

lint-githubactions:
	actionlint

lint-githubaction-scripts:
	shellcheck scripts/*.sh
	shellcheck .github/scripts/*.sh

test: compile-node
	npm run test --workspace packages/cdk

clean:
	rm -rf packages/cdk/coverage
	rm -rf packages/cdk/lib
	rm -rf cdk.out

deep-clean: clean
	rm -rf .venv
	find . -name 'node_modules' -type d -prune -exec rm -rf '{}' +

check-licenses: check-licenses-node check-licenses-python

check-licenses-node:
	npm run check-licenses --workspace packages/cdk

check-licenses-python:
	scripts/check_python_licenses.sh

aws-configure:
	aws configure sso --region eu-west-2

aws-login:
	aws sso login --sso-session sso-session

cfn-guard:
	./scripts/run_cfn_guard.sh

cdk-deploy: guard-stack_name
	REQUIRE_APPROVAL="$${REQUIRE_APPROVAL:-any-change}" && \
	VERSION_NUMBER="$${VERSION_NUMBER:-undefined}" && \
	COMMIT_ID="$${COMMIT_ID:-undefined}" && \
		npx cdk deploy \
		--app "npx ts-node --prefer-ts-exts packages/cdk/bin/EpsAssistMeApp.ts" \
		--all \
		--ci true \
		--require-approval $${REQUIRE_APPROVAL} \
		--context accountId=$$ACCOUNT_ID \
		--context stackName=$$stack_name \
		--context versionNumber=$$VERSION_NUMBER \
		--context commitId=$$COMMIT_ID \
		--context logRetentionInDays=$$LOG_RETENTION_IN_DAYS

cdk-synth: download-get-secrets-layer
	npx cdk synth \
		--quiet \
		--app "npx ts-node --prefer-ts-exts packages/cdk/bin/EpsAssistMeApp.ts" \
		--context accountId=undefined \
		--context stackName=epsam \
		--context versionNumber=undefined \
		--context commitId=undefined \
		--context logRetentionInDays=30

cdk-diff:
	npx cdk diff \
		--app "npx ts-node --prefer-ts-exts packages/cdk/bin/EpsAssistMeApp.ts" \
		--context accountId=$$ACCOUNT_ID \
		--context stackName=$$stack_name \
		--context versionNumber=$$VERSION_NUMBER \
		--context commitId=$$COMMIT_ID \
		--context logRetentionInDays=$$LOG_RETENTION_IN_DAYS

cdk-watch: guard-stack_name
	REQUIRE_APPROVAL="$${REQUIRE_APPROVAL:-any-change}" && \
	VERSION_NUMBER="$${VERSION_NUMBER:-undefined}" && \
	COMMIT_ID="$${COMMIT_ID:-undefined}" && \
		npx cdk deploy \
		--app "npx ts-node --prefer-ts-exts packages/cdk/bin/EpsAssistMeApp.ts" \
		--watch \
		--all \
		--ci true \
		--require-approval $${REQUIRE_APPROVAL} \
		--context accountId=$$ACCOUNT_ID \
		--context stackName=$$stack_name \
		--context versionNumber=$$VERSION_NUMBER \
		--context commitId=$$COMMIT_ID \
		--context logRetentionInDays=$$LOG_RETENTION_IN_DAYS
