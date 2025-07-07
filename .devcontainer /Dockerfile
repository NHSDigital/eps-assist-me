FROM python:3.12 as python-base


ENV PYTHONDONTWRITEBYTECODE 1 \
    PYTHONUNBUFFERED 1

RUN apt-get update \
    && apt-get install curl -y \
    && curl -sSL https://install.python-poetry.org | python 

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /usr/app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi



FROM python-base as eps-bot
WORKDIR /app
COPY slackbot/ .
COPY eps_corpus.db eps_corpus.db

CMD [ "python3", "-u", "app.py"]
