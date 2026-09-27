# Phase 16 Validation and Merge Criteria

## Documentation checks

1. All required Phase 16 topics are present: API contract, architecture decisions, configuration, migrations/deployment, supported formats/limits, security, operations/recovery, release checklist, and Document Understanding boundary.
2. Internal links resolve, examples use safe placeholders, terminology matches the implementation, and no documentation exposes secrets, tokens, binary contents, or production-only credentials.
3. The documented supported formats, limits, lifecycle states, errors, identifiers, configuration names, queue/retry behavior, and ownership rules match the implementation and generated OpenAPI contract.
4. Deferred behavior, provider-specific assumptions, and release blockers are explicitly labeled.

## Developer and deployment validation

1. A clean environment can follow the documented prerequisites, configure safe local values, start dependencies, apply migrations, and run the service.
2. The documented unit, API, integration, lint, and formatting commands execute successfully, or any environment-specific prerequisite is clearly stated.
3. Migration and deployment instructions identify dependency order, health/readiness expectations, and safe stop or rollback conditions.
4. Configuration documentation covers every required environment-backed setting without hard-coded secrets or credentials.

## API and operational validation

1. An authenticated consumer can follow the documented single-upload flow and understand the accepted response, validation failures, ownership restrictions, and asynchronous status behavior.
2. Operators can identify the document, artifact, job, outbox/message, retry, and recovery context from the documented identifiers and runbook links.
3. Documentation states that PostgreSQL stores metadata, storage preserves immutable originals, RabbitMQ messages contain references rather than bytes, and retries can use the original artifact.
4. The documented future-format extension path preserves validation, ownership, immutability, transaction, and downstream-boundary invariants.
5. The Document Understanding boundary is explicit and excludes OCR, semantic extraction, classification, embeddings, RAG, legal analysis, and Shariah analysis from ingestion.

## Merge decision

Merge is allowed when the documentation is complete and implementation-aligned, the clean-environment and documented verification commands pass, links/examples/security checks pass, and no unreviewed release blocker or contradiction with `mission.md`, `roadmap.md`, or `tech-stack.md` remains.
