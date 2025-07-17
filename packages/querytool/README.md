# Query Tool

This module powers EPS Assist's ability to interpret technical queries by leveraging EPS documentation and returning answers generated from retrieved context.

It uses LangChain, semantic embeddings, and DuckDB to provide retrieval-augmented generation (RAG) for queries related to EPS APIs, SCAL, and other NHS documentation.

## Prerequisites

All runtime and development dependencies (Python, Node, Poetry, Widdershins, etc.) are installed automatically when you open the project in the devcontainer.

Environment variables required for authentication are managed via `.envrc`.

Ensure your .envrc file includes the following:

```bash
export TOKENIZERS_PARALLELISM=false
export BEDROCK_MODEL_ID=<your_bedrock_model_id>
export AWS_BEARER_TOKEN_BEDROCK=<your_bearer_token>
```

If you're working outside the devcontainer, you can install all dependencies manually by running:

```bash
make install
```

## Preparing the Document Corpus

Before the assistant can answer queries, the EPS documentation must be parsed and embedded into a searchable vector store (DuckDB).

### 1. Convert SCAL CSVs to Markdown

```bash
poetry run python packages/querytool/eps_assist/preprocessors/prepare_scal.py
```

### 2. Convert OAS JSON to Markdown

This pulls the latest NHS OpenAPI specification and converts it to Markdown using Widdershins.

> **Note**: To suppress noisy Node.js warnings during the conversion, use the `NODE_NO_WARNINGS=1` environment variable as shown below.

```bash
NODE_NO_WARNINGS=1 poetry run python packages/querytool/eps_assist/preprocessors/prepare_oas.py
```

### 3. Build or Rebuild the Vector Store

This loads all Markdown files into DuckDB with semantic chunking and embeddings.

```bash
poetry run python packages/querytool/eps_assist/transform.py
```

A new `eps_corpus.db` file will be created in the same directory.

## Running Queries Locally

You can run sample questions against the vector store directly:

```bash
poetry run python packages/querytool/eps_assist/query.py
```

This script:
- Connects to `eps_corpus.db`
- Retrieves relevant document chunks
- Sends the prompt to Claude 3 via Amazon Bedrock
- Outputs the model's answer in your terminal

## Notes

- Ensure that `eps_corpus.db` exists before querying. If in doubt, re-run the transformation step.
- Claude 3 is accessed using the AWS Bedrock API via `boto3` and LangChain.
- Vector storage is file-based (DuckDB), so no external database or service is required.
- Environment variables (e.g., AWS credentials) are expected to be managed via `.envrc` in the project root.

## File Structure Overview

```
eps_assist/
├── docs/               # Source documentation (.md) for SCAL, OAS, etc.
├── preprocessors/      # Scripts for cleaning and converting raw files
├── query.py            # Executes a full question-answering example
├── transform.py        # Converts docs to vector store (DuckDB)

preprocessors/
├── prepare_scal.py     # Converts SCAL CSV to Markdown
├── prepare_oas.py      # Fetches & converts OpenAPI to Markdown
```

This module is a self-contained tool that can also be used outside of Slack for testing or integration in other EPS-related projects.
