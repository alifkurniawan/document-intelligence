# Phase 2 Validation and Merge Criteria

## Automated checks

The feature is eligible for merge only when all of the following pass from a clean checkout using documented commands:

1. Dependency installation succeeds from `uv.lock` with Python 3.14.
2. Ruff formatting/check commands pass.
3. Ruff linting passes.
4. The full pytest suite passes.
5. Configuration tests run without network access or production credentials.

## Configuration behavior

1. A settings object can be constructed in the documented development/test mode without production secrets.
2. Explicit environment variables override documented defaults deterministically.
3. Every in-scope setting has a documented type, name, requiredness, and default or failure rule.
4. Invalid URLs, enums, booleans, numeric limits, lists, MIME types, and extensions produce actionable validation errors.
5. Production-required settings fail clearly when absent or malformed.
6. Unsafe values such as non-positive upload limits or empty required allowlists are rejected.
7. API host/port, log level, supported extensions/MIME types, and upload limits are configurable and validated.
8. RabbitMQ configuration expresses exactly three retries, exponential backoff, and DLQ routing after retry exhaustion.
9. Settings construction does not connect to PostgreSQL, RabbitMQ, Firebase, or storage.

## Security and architecture review

1. No secrets, service-account material, or real connection strings are committed.
2. Secret-bearing settings are not exposed in ordinary string representations, logs, or validation messages.
3. `.env.example` contains placeholders only and documents all in-scope variables.
4. Application code has one configuration boundary rather than scattered direct environment access.
5. `/health` remains usable without external infrastructure.
6. The phase does not implement ingestion, file validation, persistence, messaging, authentication, storage, or Document Understanding behavior.

## Documentation review

1. Local setup explains how to copy/use `.env.example` safely.
2. The configuration reference matches the implementation and tests.
3. Deferred settings or provider-specific decisions are explicitly marked as follow-ups.

## Merge decision

Merge is allowed when the automated checks, configuration behavior, security/architecture review, and documentation review pass; the implementation matches the confirmed `requirements.md`; and the final diff contains no unrelated changes. Any unresolved choice must be recorded as a follow-up or confirmed before implementation.
