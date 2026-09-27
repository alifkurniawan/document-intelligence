# Legal Document Intelligence Platform

Phase 2 adds typed, environment-driven configuration to the runnable service foundation.
The service exposes an unauthenticated `GET /health` liveness endpoint and an
authenticated single-document upload endpoint. The upload workflow stores originals
outside PostgreSQL, persists metadata, and returns a queued status; extraction and
RabbitMQ publishing remain out of scope.

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
in later phases. Local uploads use `STORAGE_BACKEND=filesystem` and write under
`STORAGE_ROOT`; production requires Firebase Storage and Firebase email-auth tokens.

## Single-document upload

After configuring PostgreSQL, Firebase, and storage, upload a document with a Firebase
ID token:

```shell
curl -X POST http://127.0.0.1:8000/documents \
  -H "Authorization: Bearer $FIREBASE_ID_TOKEN" \
  -F "file=@contract.pdf"
```

Supported inputs are PDF, JPEG, PNG, DOCX, and XLSX, subject to the configured size,
extension, and MIME allowlists. PostgreSQL stores metadata and storage references only.

## Database migrations and integration tests

The database boundary uses async SQLAlchemy sessions and Alembic. Start the local
PostgreSQL integration profile with Docker Compose:

```shell
docker compose --profile integration up -d postgres
DATABASE_URL=postgresql://app:app@localhost:5432/app uv run alembic upgrade head
INTEGRATION_DATABASE_URL=postgresql://app:app@localhost:5432/app uv run pytest tests/integration
docker compose --profile integration down
```

The initial migration creates document, artifact, and processing-job metadata tables.
It stores no binary document contents. Repository operations are async and owner-scoped;
the registration service will create the initial processing job in a later phase.

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
