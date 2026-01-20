guard-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
	fi

.PHONY: install build test publish release clean

install: install-python install-hooks install-node

install-python:
	poetry sync --all-groups

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

lint: lint-githubactions lint-githubaction-scripts lint-black lint-flake8 lint-node

lint-node:
	npm run lint --workspace packages/cdk

lint-githubactions:
	actionlint

lint-githubaction-scripts:
	shellcheck ./scripts/*.sh
	shellcheck .github/scripts/*.sh

lint-black:
	poetry run black .

lint-flake8:
	poetry run flake8 .

test:
	cd packages/slackBotFunction && PYTHONPATH=. COVERAGE_FILE=coverage/.coverage poetry run python -m pytest
	cd packages/syncKnowledgeBaseFunction && PYTHONPATH=. COVERAGE_FILE=coverage/.coverage poetry run python -m pytest
	cd packages/bedrockLoggingConfigFunction && PYTHONPATH=. COVERAGE_FILE=coverage/.coverage poetry run python -m pytest

clean:
	rm -rf packages/cdk/coverage
	rm -rf packages/cdk/lib
	rm -rf packages/slackBotFunction/coverage
	rm -rf packages/slackBotFunction/.coverage
	rm -rf packages/slackBotFunction/.dependencies
	rm -rf packages/syncKnowledgeBaseFunction/coverage
	rm -rf .dependencies/
	rm -rf cdk.out
	rm -rf .build
	rm -rf .local_config
	rm -rf cfn_guard_output
	find . -name '.pytest_cache' -type d -prune -exec rm -rf '{}' +

deep-clean: clean
	rm -rf .venv
	rm -rf .poetry
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

cdk-deploy: guard-STACK_NAME
	REQUIRE_APPROVAL="$${REQUIRE_APPROVAL:-any-change}" && \
	VERSION_NUMBER="$${VERSION_NUMBER:-undefined}" && \
	COMMIT_ID="$${COMMIT_ID:-undefined}" && \
		npx cdk deploy \
		--app "npx ts-node --prefer-ts-exts packages/cdk/bin/EpsAssistMeApp.ts" \
		--all \
		--ci true \
		--require-approval $${REQUIRE_APPROVAL} \
		--context accountId=$$ACCOUNT_ID \
		--context stackName=$$STACK_NAME \
		--context versionNumber=$$VERSION_NUMBER \
		--context commitId=$$COMMIT_ID \
		--context logRetentionInDays=$$LOG_RETENTION_IN_DAYS \
		--context slackBotToken=$$SLACK_BOT_TOKEN \
		--context slackSigningSecret=$$SLACK_SIGNING_SECRET

cdk-synth: cdk-synth-pr cdk-synth-non-pr

cdk-synth-non-pr:
	mkdir -p .dependencies/slackBotFunction
	mkdir -p .dependencies/syncKnowledgeBaseFunction
	mkdir -p .dependencies/notifyS3UploadFunction
	mkdir -p .dependencies/bedrockLoggingConfigFunction
	mkdir -p .local_config
	STACK_NAME=epsam \
	COMMIT_ID=undefined \
	VERSION_NUMBER=undefined \
	SLACK_BOT_TOKEN=dummy_token \
	SLACK_SIGNING_SECRET=dummy_secret \
	LOG_RETENTION_IN_DAYS=30 \
	LOG_LEVEL=debug \
	RUN_REGRESSION_TESTS=true \
		 ./.github/scripts/fix_cdk_json.sh .local_config/epsam.config.json
	CONFIG_FILE_NAME=.local_config/epsam.config.json npx cdk synth \
		--quiet \
		--app "npx ts-node --prefer-ts-exts packages/cdk/bin/EpsAssistMeApp.ts"

cdk-synth-pr:
	mkdir -p .dependencies/slackBotFunction
	mkdir -p .dependencies/syncKnowledgeBaseFunction
	mkdir -p .dependencies/notifyS3UploadFunction
	mkdir -p .dependencies/bedrockLoggingConfigFunction
	mkdir -p .local_config
	STACK_NAME=epsam-pr-123 \
	COMMIT_ID=undefined \
	VERSION_NUMBER=undefined \
	SLACK_BOT_TOKEN=dummy_token \
	SLACK_SIGNING_SECRET=dummy_secret \
	LOG_RETENTION_IN_DAYS=30 \
	LOG_LEVEL=debug \
	RUN_REGRESSION_TESTS=true \
		 ./.github/scripts/fix_cdk_json.sh .local_config/epsam.config.json
	CONFIG_FILE_NAME=.local_config/epsam.config.json npx cdk synth \
		--quiet \
		--app "npx ts-node --prefer-ts-exts packages/cdk/bin/EpsAssistMeApp.ts"

cdk-diff:
	npx cdk diff \
		--app "npx ts-node --prefer-ts-exts packages/cdk/bin/EpsAssistMeApp.ts" \
		--context accountId=$$ACCOUNT_ID \
		--context stackName=$$STACK_NAME \
		--context versionNumber=$$VERSION_NUMBER \
		--context commitId=$$COMMIT_ID \
		--context logRetentionInDays=$$LOG_RETENTION_IN_DAYS

cdk-watch:
	./scripts/run_sync.sh

sync-docs:
	./scripts/sync_docs.sh

convert-docs:
	poetry run python scripts/convert_docs_to_markdown.py

convert-docs-file:
	@if [ -z "$$FILE" ]; then \
		echo "usage: FILE=your_doc.pdf make convert-docs-file"; \
		exit 1; \
	fi
	poetry run python scripts/convert_docs_to_markdown.py --file "$$FILE"


compile:
	echo "Does nothing currently"
