# Phase 1 Validation and Merge Criteria

## Automated checks

The feature is eligible for merge only when all of the following pass from a clean checkout using documented commands:

1. Dependency installation succeeds from `uv.lock` with Python 3.14.
2. Ruff formatting/check commands pass without unexplained exclusions.
3. Ruff linting passes.
4. The full pytest suite passes.
5. The application imports successfully without requiring production secrets or external services.

## API behavior

1. Start the service using the documented local command.
2. `GET /health` returns HTTP 200.
3. The response JSON is exactly:

   ```json
   {"status": "ok"}
   ```

4. The endpoint works without an authentication header.
5. The endpoint works when PostgreSQL, RabbitMQ, Firebase, and object storage are unavailable or unconfigured.
6. No additional public endpoint is introduced by Phase 1.

## Container validation

1. The Docker image builds without copying `.env`, service-account keys, or other credentials.
2. The container starts with the documented command.
3. A request to the container's `/health` endpoint returns HTTP 200 and the agreed JSON body.
4. The Compose configuration is syntactically valid and does not require production credentials for the foundation smoke test.

## CI validation

1. The CI workflow is triggered for pull requests and the primary branch.
2. CI installs the locked dependency set.
3. CI runs formatting/check, lint, and tests.
4. CI succeeds without access to Firebase, PostgreSQL, RabbitMQ, or external storage.

## Architecture and security review

1. Application bootstrap remains separate from future domain, repository, and infrastructure responsibilities.
2. Logging does not expose secrets, tokens, uploaded content, or document binaries.
3. Configuration is environment-driven; no credentials or connection strings are hard-coded.
4. No binary document content is added to the repository, PostgreSQL, or RabbitMQ configuration.
5. No Document Understanding capability or ingestion workflow is implemented.
6. The implementation uses a modular monolith and introduces no unnecessary service boundary.

## Merge decision

Merge is allowed when all automated checks, API checks, container checks, and architecture/security checks above pass, the implementation matches `requirements.md`, and the final diff contains no unrelated changes. Any deferred choice—such as dependency readiness checks, structured production logging, or external-service integration—must be recorded as a follow-up rather than silently included in Phase 1.
