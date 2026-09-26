# Phase 1 Feature Specification — Project Foundation

## Context

This phase is the first implementation increment from [the roadmap](../roadmap.md). It establishes a runnable, maintainable Python service before ingestion behavior is added. The constitution requires a pragmatic modular monolith, clear API/application/domain/infrastructure boundaries, environment-driven configuration, reproducible dependencies, and small independently verifiable increments.

This phase must not implement document ingestion, authentication flows, storage, database persistence, RabbitMQ processing, normalization, or Document Understanding. It creates the seams and operational baseline that later phases will use.

## Scope

The implementation must provide:

1. A conventional Python package structure using `app/` for application code and `tests/` for tests.
2. A FastAPI application entry point that can start locally.
3. `GET /health` returning HTTP 200 and a minimal JSON response:

   ```json
   {"status": "ok"}
   ```

4. A basic application logging setup suitable for local development and future structured logging.
5. A development and test command surface documented in the repository.
6. A Dockerfile for running the API in a reproducible container.
7. A local Docker Compose definition for the application foundation and its future service dependencies, without requiring implementation of PostgreSQL, RabbitMQ, or Firebase behavior in this phase.
8. A CI workflow that installs the locked dependencies and runs the agreed quality checks and tests.
9. Baseline tests proving application startup and the health endpoint.

## Decisions

### Runtime and dependency management

* Use Python 3.14, as required by the constitution.
* Keep the existing `pyproject.toml` and `uv.lock` as the dependency source of truth.
* Use FastAPI for HTTP and pytest for tests.
* Use Ruff for linting and formatting; add it to development dependencies if it is not already available.
* Do not add database, Firebase, RabbitMQ, or document-processing implementation to the foundation solely to make containers appear complete.

### Package structure

Use a conventional structure that leaves room for later layers without prematurely implementing them:

```text
app/
  main.py
  api/
  application/
  domain/
  infrastructure/
tests/
  test_health.py
```

Only the modules needed for the health endpoint and application bootstrap are required now. Empty future-layer directories should be created only when they contain a meaningful package marker or documented placeholder.

### Health endpoint

* Endpoint: `GET /health`.
* Success status: HTTP 200.
* Response body: exactly the minimal status object unless a later specification changes the contract.
* The endpoint must not require authentication or external infrastructure in Phase 1.
* The endpoint is a liveness check, not a readiness check. Dependency health checks belong to a later operational specification.

### Logging

Configure logging once at application startup with a predictable level controlled by environment configuration where practical. Do not log credentials, tokens, uploaded content, or future document binary data. Request correlation IDs and fully structured production logging are deferred to the error-handling phase.

### Docker

Provide a small production-shaped application image and a local Compose file. The image must run the API using an explicit command, expose the API port, and receive configuration through environment variables. Compose may define placeholders or profiles for PostgreSQL and RabbitMQ, but Phase 1 acceptance does not require those services to be consumed by the application.

### CI

CI must run on the repository's primary branch and pull requests. It must install from the lockfile and run formatting/lint checks plus the test suite. CI must not require production Firebase credentials or access to external document storage.

## Constraints and non-goals

* Do not introduce microservices.
* Do not hard-code secrets, connection strings, Firebase credentials, or environment-specific values.
* Do not add an alternate canonical document representation.
* Do not implement OCR, LLM/VLM processing, classification, extraction, legal analysis, Shariah analysis, embeddings, RAG, or any other Document Understanding behavior.
* Do not make `/health` depend on PostgreSQL, RabbitMQ, Firebase, or storage.
* Do not broaden the public API beyond `/health` in this phase.

## Future compatibility

The foundation should allow later phases to add configuration, database sessions, repositories, storage adapters, authentication, and RabbitMQ publishers without moving the API entry point or rewriting the health contract. The structure is an organizational seam, not a mandate to create speculative abstractions.
