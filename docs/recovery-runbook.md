# Recovery runbook

Recovery is operator-triggered in the first release. It is bounded, auditable,
and conservative: it never deletes an original artifact or marks processing
complete without durable evidence.

## Diagnose

Use the request `X-Correlation-ID`, document ID, job ID, and outbox ID to join
API logs, database rows, and broker events. Logs contain identifiers and error
classes only; never copy tokens or document bytes into an incident ticket.

Check service health, database migration state, the processing queue, and the
DLQ before retrying anything. A queued job with an unpublished outbox row is a
publication problem, not a downstream processing problem.

## Metrics and alerts

Export the in-process counters through the deployment's metrics adapter. The
minimum alert set is: sustained `api_unexpected_failures` or dependency
failures above 1% for five minutes; any growth in `recovery_candidates`;
retry/DLQ growth for ten minutes; and an outbox pending age above five minutes.
`api_validation_failures` is an operational trend, not an outage by itself.

## Reconcile

Run a dry-run reconciliation first. The implementation's
`SqlAlchemyRecoverySource` reports only conservative candidates such as a
stored/queued document without an original artifact. Review every candidate
and its ownership before taking action. Re-running the same dry run is safe.

The current release intentionally does not perform automatic destructive
cleanup or periodic reconciliation. Add scheduling only with an explicit
ownership and retention decision.

## Retry

Retry only durable, unpublished outbox rows through `OutboxDispatcher`; do not
publish hand-written messages. Publisher confirmation is required before an
outbox row is marked published. A failed attempt remains pending and can be
retried on the next bounded dispatcher run.

Downstream retries use the three-attempt exponential policy. Permanent failures
and exhausted transient failures are visible as `failed` and are routed to the
DLQ. Duplicate delivery is expected; consumers must use `job_id`/`document_id`
idempotently and must not replace the original artifact.

## Stop and escalate

Stop if ownership is ambiguous, the original artifact cannot be verified, a
database transaction is unhealthy, or the same outbox publication repeatedly
fails. Preserve the correlation ID and relevant identifiers, then escalate to
the service owner. Never delete rows or storage objects as an incident shortcut.

## Local integration checks

```shell
docker compose --profile integration up -d postgres rabbitmq
DATABASE_URL=postgresql://app:app@localhost:5432/app uv run alembic upgrade head
INTEGRATION_DATABASE_URL=postgresql://app:app@localhost:5432/app uv run pytest tests/integration
docker compose --profile integration down
```

These commands use isolated local credentials and do not require production
Firebase credentials. The focused test suite uses in-memory storage and static
token verification.
