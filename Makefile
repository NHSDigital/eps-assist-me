guard-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
	fi

.PHONY: install build test publish release clean

install: install-python install-hooks

install-python:
	poetry install

install-hooks: install-python
	poetry run pre-commit install --install-hooks --overwrite

pre-commit: git-secrets-docker-setup
	poetry run pre-commit run --all-files

git-secrets-docker-setup:
	export LOCAL_WORKSPACE_FOLDER=$(pwd)
	docker build -f https://raw.githubusercontent.com/NHSDigital/eps-workflow-quality-checks/refs/tags/v4.0.4/dockerfiles/nhsd-git-secrets.dockerfile -t git-secrets .

check-licenses-python:
	scripts/check_python_licenses.sh
