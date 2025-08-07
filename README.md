# EPS Assist Me
![Build](https://github.com/NHSDigital/eps-assist-me/workflows/release/badge.svg?branch=main)

This is a Slack-based AI assistant that helps people query and understand documents relating to onboarding to the FHIR NHS EPS API (used for prescriptions and dispensing). The assistant uses Amazon Bedrock Knowledge Base with OpenSearch Serverless to provide intelligent responses to user queries through Slack slash commands.

## Architecture

The solution consists of:

- **Slack Bot Function**: AWS Lambda function that handles Slack slash commands and integrates with Amazon Bedrock Knowledge Base
- **Create Index Function**: AWS Lambda function that creates and manages OpenSearch vector indices for the knowledge base
- **OpenSearch Serverless**: Vector database for storing and searching document embeddings
- **Amazon Bedrock Knowledge Base**: RAG (Retrieval-Augmented Generation) service with guardrails
- **S3 Storage**: Document storage for the knowledge base
- **AWS CDK**: Infrastructure as Code for deployment

## Project Structure

This is a monorepo with the following structure:

```
packages/
├── cdk/                   # AWS CDK infrastructure code
│   ├── bin/               # CDK app entry point
│   ├── constructs/        # Reusable CDK constructs
│   ├── resources/         # AWS resource definitions
│   └── stacks/            # CDK stack definitions
├── createIndexFunction/   # Lambda function for OpenSearch index management
└── slackBotFunction/      # Lambda function for Slack bot integration
```

## Contributing

Contributions to this project are welcome from anyone, providing that they conform to the [guidelines for contribution](https://github.com/NHSDigital/eps-assist-me/blob/main/CONTRIBUTING.md) and the [community code of conduct](https://github.com/NHSDigital/eps-assist-me/blob/main/CODE_OF_CONDUCT.md).

### Licensing

This code is dual licensed under the MIT license and the OGL (Open Government License). Any new work added to this repository must conform to the conditions of these licenses. In particular this means that this project may not depend on GPL-licensed or AGPL-licensed libraries, as these would violate the terms of those libraries' licenses.

The contents of this repository are protected by Crown Copyright (C).

## Development

It is recommended that you use visual studio code and a devcontainer as this will install all necessary components and correct versions of tools and languages.  
See https://code.visualstudio.com/docs/devcontainers/containers for details on how to set this up on your host machine.  
There is also a workspace file in .vscode that should be opened once you have started the devcontainer. The workspace file can also be opened outside of a devcontainer if you wish.  

All commits must be made using [signed commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits)

Once the steps at the link above have been completed. Add to your ~/.gnupg/gpg.conf as below:

```
use-agent
pinentry-mode loopback
```

and to your ~/.gnupg/gpg-agent.conf as below:

```
allow-loopback-pinentry
```

As described here:
https://stackoverflow.com/a/59170001

You will need to create the files, if they do not already exist.
This will ensure that your VSCode bash terminal prompts you for your GPG key password.

You can cache the gpg key passphrase by following instructions at https://superuser.com/questions/624343/keep-gnupg-credentials-cached-for-entire-user-session

### Setup

Ensure you have the following lines in the file .envrc

```bash
export AWS_DEFAULT_PROFILE=prescription-dev
```

Once you have saved .envrc, start a new terminal in vscode and run this command to authenticate against AWS

```bash
make aws-configure
```

Put the following values in:

```text
SSO session name (Recommended): sso-session
SSO start URL [None]: <USE VALUE OF SSO START URL FROM AWS LOGIN COMMAND LINE ACCESS INSTRUCTIONS ACCESSED FROM https://myapps.microsoft.com>
SSO region [None]: eu-west-2
SSO registration scopes [sso:account:access]:
```

This will then open a browser window and you should authenticate with your hscic credentials
You should then select the development account and set default region to be eu-west-2.

You will now be able to use AWS and SAM CLI commands to access the dev account. You can also use the AWS extension to view resources.

When the token expires, you may need to reauthorise using `make aws-login`

### Environment Variables

For deployment, the following environment variables are required:

- `ACCOUNT_ID`: AWS Account ID
- `STACK_NAME`: Name of the CloudFormation stack
- `VERSION_NUMBER`: Version number for the deployment
- `COMMIT_ID`: Git commit ID
- `LOG_RETENTION_IN_DAYS`: CloudWatch log retention period
- `SLACK_BOT_TOKEN`: Slack bot OAuth token
- `SLACK_SIGNING_SECRET`: Slack app signing secret

### CI Setup

The GitHub Actions require a secret to exist on the repo called "SONAR_TOKEN".
This can be obtained from [SonarCloud](https://sonarcloud.io/)
as described [here](https://docs.sonarsource.com/sonarqube/latest/user-guide/user-account/generating-and-using-tokens/).
You will need the "Execute Analysis" permission for the project (NHSDigital_eps-assist-me) in order for the token to work.

### Pre-commit hooks

Some pre-commit hooks are installed as part of the install above, to run basic lint checks and ensure you can't accidentally commit invalid changes.
The pre-commit hook uses python package pre-commit and is configured in the file .pre-commit-config.yaml.
A combination of these checks are also run in CI.

### Make commands

There are `make` commands that are run as part of the CI pipeline and help alias some functionality during development.

#### Install targets

- `install-node` Installs node dependencies.
- `install-python` Installs python dependencies.
- `install-hooks` Installs git pre commit hooks.
- `install` Runs all install targets.

#### CDK targets
These are used to do common commands related to cdk

- `cdk-deploy` Builds and deploys the code to AWS. Requires `STACK_NAME` environment variable.
- `cdk-synth` Converts the CDK code to cloudformation templates.
- `cdk-diff` Runs cdk diff, comparing the deployed stack with the local CDK code to identify differences.
- `cdk-watch` Syncs the code and CDK templates to AWS. This keeps running and automatically uploads changes to AWS. Requires `STACK_NAME` environment variable.

#### Clean and deep-clean targets

- `clean` Clears up any files that have been generated by building or testing locally.
- `deep-clean` Runs clean target and also removes any node_modules and python libraries installed locally.

#### Linting and testing

- `lint` Runs lint for GitHub Actions and scripts.
- `lint-black` Runs black formatter on Python code.
- `lint-flake8` Runs flake8 linter on Python code.
- `lint-githubactions` Lints the repository's GitHub Actions workflows.
- `lint-githubaction-scripts` Lints all shell scripts in `.github/scripts` using ShellCheck.
- `test` Runs unit tests for CDK code.
- `cfn-guard` Runs cfn-guard against CDK resources.
- `pre-commit` Runs pre-commit hooks on all files.

#### Compiling

- `compile-node` Runs TypeScript compiler (tsc) for the project.

#### Check licenses

- `check-licenses` Checks licenses for all packages. This command calls both check-licenses-node and check-licenses-python.
- `check-licenses-node` Checks licenses for all node code.
- `check-licenses-python` Checks licenses for all python code.

#### CLI Login to AWS

- `aws-configure` Configures a connection to AWS.
- `aws-login` Reconnects to AWS using a previously configured connection.

### GitHub folder

This .github folder contains workflows and templates related to GitHub, along with actions and scripts pertaining to Jira.

- `dependabot.yml` Dependabot definition file.
- `pull_request_template.yml` Template for pull requests.

Actions are in the `.github/actions` folder:

- `mark_jira_released` Action to mark Jira issues as released.
- `update_confluence_jira` Action to update Confluence with Jira issues.

Scripts are in the `.github/scripts` folder:

- `call_mark_jira_released.sh` Calls a Lambda function to mark Jira issues as released.
- `check-sbom-issues-against-ignores.sh` Validates SBOM scan against ignore list and reports unignored critical issues.
- `create_env_release_notes.sh` Generates release notes for a specific environment using a Lambda function.
- `delete_stacks.sh` Checks and deletes active CloudFormation stacks associated with closed pull requests.
- `fix_cdk_json.sh` Updates context values in `cdk.json` using environment variables before deployment.
- `get_current_dev_tag.sh` Retrieves the current development tag and sets it as an environment variable.
- `get_target_deployed_tag.sh` Retrieves the currently deployed tag and sets it as an environment variable.

Workflows are in the `.github/workflows` folder:

- `combine-dependabot-prs.yml` Workflow for combining dependabot pull requests. Runs on demand.
- `delete_old_cloudformation_stacks.yml` Workflow for deleting old cloud formation stacks. Runs daily.
- `dependabot_auto_approve_and_merge.yml` Workflow to auto merge dependabot updates.
- `pr_title_check.yml` Checks PR titles for required prefix and ticket or dependabot reference.
- `pr-link.yaml` This workflow template links Pull Requests to Jira tickets and runs when a pull request is opened.
- `pull_request.yml` Called when pull request is opened or updated. Packages and deploys the code to dev AWS account for testing.
- `release.yml` Runs on demand to create a release and deploy to all environments.
- `cdk_package_code.yml` Packages code into a docker image and uploads to a github artifact for later deployment.
- `cdk_release_code.yml` Release code built by cdk_package_code.yml to an environment.
- `ci.yml` Continuous integration workflow for quality checks and testing.
