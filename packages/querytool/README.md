# Query tool

This is the tool that augments incoming user queries with EPS specific data.

## Prerequisites

- Python 3.12
- Poetry
- .env file 

Widdershins:

    npm install -g widdershins

Load environment variables:

    source .env

To set up run:

    poetry install

## Updating corpus

To prepare the SCAL files for processing, run:

    poetry run python querytool/eps_assist/preprocessors/prepare_scal.py

To prepare the OAS file for processing, run:

    poetry run python querytool/eps_assist/preprocessors/prepare_oas.py

To run the ingestion and transformation of documents into the vector store, run:

    poetry run python querytool/eps_assist/transform.py

## Running samples queries

To run a query, run:

    poetry run python querytool/eps_assist/query.py
