SHELL = /bin/bash
.SHELLFLAGS = -o pipefail -c
export CDK_CONFIG_versionNumber=undefined
export CDK_CONFIG_commitId=undefined
export CDK_CONFIG_logRetentionInDays=30
export CDK_CONFIG_logLevel=DEBUG
export CDK_CONFIG_forwardCsocLogs=false
export CDK_CONFIG_environment=dev

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
	cd packages/preprocessingFunction && PYTHONPATH=. COVERAGE_FILE=coverage/.coverage poetry run python -m pytest
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

cdk-synth: cdk-synth-stateful cdk-synth-stateless cdk-synth-basepath-mapping

cdk-synth-stateful: cdk-synth-stateful-pr cdk-synth-stateful-non-pr
cdk-synth-stateless: cdk-synth-stateless-pr cdk-synth-stateless-non-pr

cdk-synth-stateful-pr:
	mkdir -p .dependencies/slackBotFunction
	mkdir -p .dependencies/syncKnowledgeBaseFunction
	mkdir -p .dependencies/preprocessingFunction
	mkdir -p .dependencies/bedrockLoggingConfigFunction
	mkdir -p .local_config
	CDK_APP_NAME=EpsAssistMe_StatefulApp \
	CDK_CONFIG_stackName=epsam-stateful \
	CDK_CONFIG_enableBedrockLogging=false \
	CDK_CONFIG_isPullRequest=true \
	npm run cdk-synth --workspace packages/cdk/

cdk-synth-stateful-non-pr:
	mkdir -p .dependencies/slackBotFunction
	mkdir -p .dependencies/syncKnowledgeBaseFunction
	mkdir -p .dependencies/preprocessingFunction
	mkdir -p .dependencies/bedrockLoggingConfigFunction
	mkdir -p .local_config
	CDK_APP_NAME=EpsAssistMe_StatefulApp \
	CDK_CONFIG_stackName=epsam-stateful \
	CDK_CONFIG_enableBedrockLogging=false \
	CDK_CONFIG_isPullRequest=false \
	npm run cdk-synth --workspace packages/cdk/

cdk-synth-stateless-pr:
	mkdir -p .dependencies/slackBotFunction
	mkdir -p .dependencies/syncKnowledgeBaseFunction
	mkdir -p .dependencies/preprocessingFunction
	mkdir -p .dependencies/bedrockLoggingConfigFunction
	mkdir -p .local_config
	CDK_APP_NAME=EpsAssistMe_StatelessApp \
	CDK_CONFIG_stackName=epsam-stateless \
	CDK_CONFIG_isPullRequest=true \
	CDK_CONFIG_runRegressionTests=true \
	CDK_CONFIG_forwardCsocLogs=true \
	CDK_CONFIG_slackBotToken=foo \
	CDK_CONFIG_slackSigningSecret=bar \
	CDK_CONFIG_statefulStackName=epsam-stateful \
	npm run cdk-synth --workspace packages/cdk/

cdk-synth-stateless-non-pr:
	mkdir -p .dependencies/slackBotFunction
	mkdir -p .dependencies/syncKnowledgeBaseFunction
	mkdir -p .dependencies/preprocessingFunction
	mkdir -p .dependencies/bedrockLoggingConfigFunction
	mkdir -p .local_config
	CDK_APP_NAME=EpsAssistMe_StatelessApp \
	CDK_CONFIG_stackName=epsam-stateless \
	CDK_CONFIG_isPullRequest=false \
	CDK_CONFIG_runRegressionTests=true \
	CDK_CONFIG_forwardCsocLogs=true \
	CDK_CONFIG_slackBotToken=foo \
	CDK_CONFIG_slackSigningSecret=bar \
	CDK_CONFIG_statefulStackName=epsam-stateful \
	npm run cdk-synth --workspace packages/cdk/

cdk-synth-basepath-mapping:
	mkdir -p .dependencies/slackBotFunction
	mkdir -p .dependencies/syncKnowledgeBaseFunction
	mkdir -p .dependencies/preprocessingFunction
	mkdir -p .dependencies/bedrockLoggingConfigFunction
	mkdir -p .local_config
	CDK_APP_NAME=EpsAssistMe_BasepathMappingApp \
	CDK_CONFIG_stackName=epsam-bpm \
	CDK_CONFIG_isPullRequest=false \
	CDK_CONFIG_statefulStackName=epsam-stateful \
	CDK_CONFIG_statelessStackName=epsam-stateless \
	npm run cdk-synth --workspace packages/cdk/

cdk-watch:
	./scripts/run_sync.sh

sync-docs:
	./scripts/sync_docs.sh

convert-docs:
	cd packages/preprocessingFunction && poetry run python -m app.cli

convert-docs-file:
	@if [ -z "$$FILE" ]; then \
		echo "usage: FILE=your_doc.pdf make convert-docs-file"; \
		exit 1; \
	fi
	cd packages/preprocessingFunction && poetry run python -m app.cli --file "$$FILE"


compile:
	echo "Does nothing currently"

create-npmrc:
	gh auth login --scopes "read:packages"; \
	echo "//npm.pkg.github.com/:_authToken=$$(gh auth token)" > .npmrc
	echo "@nhsdigital:registry=https://npm.pkg.github.com" >> .npmrc
