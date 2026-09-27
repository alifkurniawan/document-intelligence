# Release checklist

Complete every applicable gate before merge or deployment:

- [ ] `uv.lock` and `pyproject.toml` are consistent; no secrets or production data are committed.
- [ ] `uv run ruff format --check .`, `uv run ruff check .`, and `uv run pytest` pass.
- [ ] Integration PostgreSQL/RabbitMQ checks pass when infrastructure behavior changed.
- [ ] Alembic migrations apply cleanly in order and have a reviewed downgrade/stop plan.
- [ ] Configuration names/defaults and production-required settings match `.env.example` and `docs/configuration.md`.
- [ ] OpenAPI/API behavior, status codes, error envelope, ownership, and correlation IDs remain compatible.
- [ ] Original storage is exclusive, hash/size verified, readable, and never overwritten.
- [ ] Outbox publication uses publisher confirms; queue, retry, and DLQ settings are reviewed.
- [ ] Health, logs, metrics, correlation IDs, recovery candidates, and escalation ownership are ready.
- [ ] Authentication, least privilege, secret redaction, upload validation, and sensitive-data handling are reviewed.
- [ ] Documentation links, supported formats/limits, deployment commands, and the Document Understanding boundary are current.
- [ ] Deferred items (batch/import, normalization, production hardening) and any release blocker have an explicit owner/decision.

Operational behavior and recovery are documented in the [recovery runbook](recovery-runbook.md).
No release is complete while a known contradiction, unresolved migration failure, or
unreviewed security/recovery blocker remains.
