# Phase 2 Feature Specification — Configuration

## Context

This phase follows [Phase 1 — Project foundation](../2026-09-26-phase-01-project-foundation/requirements.md) and is the next increment in the [roadmap](../roadmap.md). It establishes one typed, environment-driven configuration contract for the modular monolith before database, storage, authentication, and message-broker behavior is implemented.

The design follows the [mission](../mission.md) and [tech stack](../tech-stack.md): infrastructure choices remain behind application boundaries, secrets are never hard-coded, and configuration must not make the service depend on external systems merely to start or test settings.

## Scope

The implementation must provide:

1. A typed settings object/module with one documented source of truth.
2. Environment loading suitable for local `.env` development and deployment-injected variables.
3. Explicit configuration for environment name, logging, API/runtime behavior, upload limits, supported extensions/MIME types, PostgreSQL, RabbitMQ, Firebase Authentication, and Firebase Storage.
4. Clear validation for missing, malformed, contradictory, or unsafe values.
5. A safe `.env.example` and configuration reference.
6. Unit tests for defaults, overrides, parsing, validation failures, and secret-safe representation.

## Decisions

The following decisions are confirmed for this specification:

* Settings are read through a typed application settings object rather than direct `os.environ` access throughout the codebase.
* Environment variables do not use a project-specific prefix. Names use a consistent uppercase and underscore convention.
* Supported environment names are `development`, `test`, and `production`.
* Production mode requires credentials and connection settings needed by enabled infrastructure; development and test modes may use fakes/local adapters and must not require production secrets.
* Configuration validation is fail-fast and reports setting names and remediation context without printing values.
* API host, API port, log level, supported file formats, and upload limits are configuration inputs.
* RabbitMQ retry policy is three retries with exponential backoff, followed by routing to a Dead Letter Queue (DLQ).
* No external service connection is opened while importing or constructing settings.

## Proposed configuration categories

The final variable names and defaults should cover, at minimum:

* application environment and log level;
* API host and port;
* maximum upload size and any related request limits;
* supported extensions and MIME types;
* PostgreSQL connection URL;
* RabbitMQ URL, exchange, queue, routing key, retry count, exponential-backoff parameters, and DLQ settings;
* Firebase project/authentication settings;
* Firebase Storage bucket and artifact path settings.

## Constraints and non-goals

* Do not implement database sessions, migrations, Firebase clients, storage adapters, RabbitMQ publishers, authentication flows, file validation, or upload endpoints in this phase.
* Do not hard-code secrets, credentials, or environment-specific connection strings.
* Do not make `/health` depend on configured external services.
* Do not add speculative settings for downstream Document Understanding, OCR, VLM/LLM processing, extraction, embeddings, RAG, or legal analysis.
* Do not silently accept invalid values by falling back to unsafe defaults.

## Deferred implementation detail

The exact exponential-backoff base delay, maximum delay, jitter policy, exchange/queue names, and DLQ topology may be selected during implementation, but they must be typed, documented, environment-configurable where operationally relevant, and covered by tests. The retry count must remain three unless a later approved phase changes the policy.

## Future compatibility

Later phases should consume this contract through dependency injection or application boundaries rather than reading environment variables directly. Adding a setting should include documentation, safe defaults where appropriate, validation behavior, and focused tests. Configuration must remain independent from Document Understanding and must not become a hidden service locator.
