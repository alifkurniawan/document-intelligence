# Legal Document Intelligence Platform

The service exposes an unauthenticated `GET /health` liveness endpoint and an
authenticated single-document ingestion workflow. It validates and immutably stores
originals outside PostgreSQL, persists metadata, and returns a queued status; Document
Understanding remains downstream. See the [API contract](docs/api.md),
[architecture](docs/architecture.md), [configuration](docs/configuration.md),
[deployment guide](docs/deployment.md), [security notes](docs/security.md), and
[release checklist](docs/release-checklist.md).

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

RabbitMQ uses one durable processing queue, publisher confirms, three bounded
exponential-backoff retries, and a durable Dead Letter Queue. Accepted uploads write a
reference-only message to a transactional PostgreSQL outbox in the same transaction as
the job; an outbox dispatcher publishes it and marks it published only after broker
confirmation. Messages contain references, never file bytes. Local uploads use
`STORAGE_BACKEND=filesystem` and write under `STORAGE_ROOT`; production requires
Firebase Storage and Firebase email-auth tokens.

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

The migrations create document, artifact, processing-job, and transactional-outbox
metadata tables. They store no binary document contents. Repository operations are async
and owner-scoped. The outbox is the recovery boundary between a committed job and
RabbitMQ publication.

Batch/import remains a deferred adapter: when introduced, it must reuse the
single-document registration workflow, report per-item results, support cancellation
and bounded concurrency, and introduce a dedicated idempotency key. Normalization is
also deferred; original artifacts remain immutable source of truth and no normalizer is
included in this slice.

## Quality checks

```shell
uv run ruff format --check .
uv run ruff check .
uv run pytest
```

To format files, run `uv run ruff format .`.

## Diagnostics and recovery

Every HTTP response includes `X-Correlation-ID`; clients may provide a safe
`X-Correlation-ID` value and the service propagates it to logs and processing
messages. Public errors use `{code, detail, correlation_id}` and never expose
provider credentials or document bytes. Metrics are defined for API failures,
outbox publication, retries, dead letters, and recovery outcomes.

Recovery is operator-triggered and dry-run-first. See
[`docs/recovery-runbook.md`](docs/recovery-runbook.md) for diagnosis,
reconciliation, bounded outbox retry, DLQ handling, and escalation.

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

PostgreSQL and RabbitMQ are available under the `integration` profile for local
boundary tests; the `foundation` profile runs the application with local defaults.

## CI

GitHub Actions runs locked dependency installation, Ruff formatting/linting, and the
pytest suite for pull requests and pushes to `main`. It requires no external service
credentials.
