# CDK Infrastructure

AWS Cloud Development Kit (CDK) application defining the EPS Assist Me infrastructure.

## What This Is

The single source of truth for the project's cloud resources.
Provisions the entire bot ecosystem in one deployable stack.

## Architecture

Provisions:

- **API Gateway** - Receives Slack events
- **Lambda Functions** - `slackBotFunction`, `preprocessingFunction`, `syncKnowledgeBaseFunction`, `notifyS3UploadFunction`, `bedrockLoggingConfigFunction`
- **Amazon Bedrock** - Knowledge Base and Data Source configuration
- **OpenSearch Serverless** - Vector database for RAG document embeddings
- **S3 Buckets** - Raw and processed document storage with event notifications
- **DynamoDB** - Bot session state and feedback storage
- **SQS** - Queue for asynchronous processing of document events
- **IAM Roles** - Least-privilege access across services

## Project Structure

- `bin/` CDK app entry point (`EpsAssistMeApp.ts`)
- `constructs/` Reusable Layer 3 (L3) components (e.g. `RestApiGateway`, `LambdaFunction`, `DynamoDbTable`)
- `resources/` L2/L1 definitions grouped by domain (e.g. `VectorKnowledgeBaseResources`, `OpenSearchResources`)
- `stacks/` The actual CloudFormation stack definition (`EpsAssistMeStack`)
- `prompts/` Text templates used to construct Bedrock prompts (System, User, Reformulation)

## Environment Variables

Configured in the stack context (`cdk.json` or via CLI).

| Variable | Purpose |
|---|---|
| `accountId` | Target AWS Account ID |
| `stackName` | CloudFormation stack name |
| `versionNumber` | Stack version |
| `commitId` | Hash for tagging |
| `logRetentionInDays` | CloudWatch retention policy |
| `slackBotToken` | The OAuth token from Slack |
| `slackSigningSecret` | The signing secret from Slack |

## Deployment Notes

- Deployment uses context variables passed during synthesis (`cdk synth --context...`)
- OpenSearch Serverless collections can take around 5-10 minutes to provision
- The Bedrock data source ingestion relies on IAM permissions that might occasionally have propagation delays on first deploy
