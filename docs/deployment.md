# Deployment and migrations

## Prerequisites

Install Python 3.14 and `uv`. Production also needs PostgreSQL, RabbitMQ, Firebase
Authentication, and Firebase Storage. The application image is built from the locked
`pyproject.toml`/`uv.lock` dependency set.

For local infrastructure:

```shell
docker compose --profile integration up -d postgres rabbitmq
cp .env.example .env
DATABASE_URL=postgresql://app:app@localhost:5432/app uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The dependency order is: database/broker availability, migration, application startup,
then traffic. `GET /health` is a liveness signal only; it does not prove that database,
Firebase, or RabbitMQ dependencies are ready. Verify those dependencies separately
before enabling upload traffic.

## Release sequence

1. Build and scan the image; inject secrets at runtime.
2. Verify database backup/restore posture and connectivity from the deployment network.
3. Run `uv run alembic upgrade head` with the release image or an equivalent migration
   environment.
4. Start the API and outbox/processing workers with the same configuration contract.
5. Check `/health`, migrations, queue/DLQ connectivity, storage access, and metrics.
6. Perform an authenticated test upload using a non-sensitive fixture.

Stop rollout if migrations fail, ownership/authentication is not verifiable, storage
cannot preserve or read originals, publisher confirms fail repeatedly, or the original
artifact cannot be reconciled. Preserve identifiers and use the [recovery runbook](recovery-runbook.md).
Do not delete metadata or storage objects as a rollback shortcut. Apply a reviewed
forward migration or restore through the deployment's approved database procedure.

## Verification commands

```shell
uv sync --dev
uv run ruff format --check .
uv run ruff check .
uv run pytest
DATABASE_URL=postgresql://app:app@localhost:5432/app uv run alembic upgrade head
INTEGRATION_DATABASE_URL=postgresql://app:app@localhost:5432/app uv run pytest tests/integration
```

The integration commands require the Compose integration profile. CI unit/API checks
use test doubles and do not require production credentials.
