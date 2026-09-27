# Legal Document Intelligence Platform

Phase 2 adds typed, environment-driven configuration to the runnable service foundation.
The service still exposes only an unauthenticated `GET /health` liveness endpoint;
document ingestion, persistence, storage, authentication, messaging, and Document
Understanding remain out of scope.

## Local development

Python 3.14 and [uv](https://docs.astral.sh/uv/) are required.

```shell
uv sync --dev
cp .env.example .env
uv run uvicorn app.main:app --reload
curl http://127.0.0.1:8000/health
```

The response is `{"status":"ok"}`. Configuration is read from unprefixed environment
variables or a local `.env` file. Supported environments are `development`, `test`, and
`production`; production requires database, RabbitMQ, and Firebase settings. See
`.env.example` for the complete reference. `LOG_LEVEL` defaults to `INFO`.

RabbitMQ configuration reserves three retries with exponential backoff, followed by
routing to the configured Dead Letter Queue. Publishing and consuming are implemented
in later phases.

## Quality checks

```shell
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

To format files, run `uv run ruff format .`.

## Container

The image uses the locked dependency set and does not copy environment files or
credentials:

```shell
docker build -t legal-document-backend .
docker run --rm -p 8000:8000 legal-document-backend
```

The foundation Compose profile runs the application only:

```shell
docker compose --profile foundation up --build
```

PostgreSQL and RabbitMQ are declared under the `future` profile as placeholders for
later phases and are not consumed by the Phase 1 application.

## CI

GitHub Actions runs locked dependency installation, Ruff formatting/linting, and the
pytest suite for pull requests and pushes to `main`. It requires no external service
credentials.
