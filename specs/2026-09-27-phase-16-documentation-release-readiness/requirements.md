# Phase 16 Feature Specification — Documentation and Release Readiness

## Context

Phase 16 makes the ingestion subsystem usable by new developers, API consumers, and operators. It follows the [mission](../mission.md), [roadmap](../roadmap.md), and [tech stack](../tech-stack.md), and assumes the preceding ingestion, asynchronous-processing, integration, and error-recovery work is available for documentation and verification.

The documentation is part of the product contract: it must describe behavior that exists, expose meaningful limitations, and make the original-artifact and asynchronous-processing invariants operationally understandable.

## Scope

The implementation must provide maintained documentation for:

1. The authenticated single-document upload API, including authentication, request encoding, validation, response fields, lifecycle/status behavior, original-artifact access, ownership, and public error responses.
2. Supported formats and limits, including PDF, scanned PDF, JPEG, PNG, allowlisted image formats, DOCX, and XLSX; MIME/extension policy; size/readability/integrity checks; and the documented extension path for adding formats.
3. The system architecture and key decisions: modular-monolith boundaries, application orchestration, domain invariants, PostgreSQL metadata, immutable external originals, storage adapters, RabbitMQ reference messages, outbox/transaction coordination, and downstream processing ownership.
4. Configuration and secrets, including all environment-backed settings, `.env.example`, required local services, Firebase Authentication/Storage setup, PostgreSQL, RabbitMQ, queue/retry settings, file limits, and environment-specific deployment configuration.
5. Migration and deployment instructions, including prerequisites, startup/dependency order, migration execution, health/readiness checks, rollback or stop conditions, and clean-environment verification.
6. Security notes covering token verification, account ownership, authorization, upload validation, immutable originals, sensitive-data handling, log/error redaction, and secret management.
7. Operational guidance for storage, queue/outbox publication, processing states, retries, dead letters, failures, correlation identifiers, and recovery, with the recovery runbook linked as the operational source of truth.
8. A release checklist that gates merge/release on tests, migrations, configuration, API compatibility, integration dependencies, security, observability, documentation, and explicit unresolved decisions.
9. A clear Document Understanding boundary: ingestion may perform technical inspection only and must not implement OCR, semantic understanding, classification, extraction, embeddings, RAG, legal analysis, or Shariah analysis.

## Confirmed decisions

1. Phase 16 is one documentation and release-readiness feature covering the full roadmap scope rather than a new runtime ingestion workflow.
2. Documentation describes the current implementation and explicitly labels deferred or provider-specific behavior; it does not invent unsupported guarantees.
3. The original uploaded artifact remains immutable source of truth. Documentation must preserve the invariant that PostgreSQL stores metadata, RabbitMQ carries references, and downstream processing can retry from the original.
4. The API contract is documented at the authenticated single-upload boundary first. Batch and import remain adapters over the same core service, not separate business workflows.
5. Configuration examples contain names and safe placeholders only. Credentials, tokens, document bytes, and production connection details must not be committed.
6. Future format support follows the existing validation/inspection and storage interfaces, with tests and documentation updated as part of the same change.

## Non-goals

Do not add a new upload channel, downstream understanding workflow, OCR or semantic processing, broad file normalization, new infrastructure provider, undocumented production automation, secret material, or a separate business workflow for batch/import.

## Completion context

The feature is complete when a new developer can follow the documented setup and run the service/tests, an API consumer can perform an authenticated single upload, an operator can understand storage/queue/retry/recovery behavior, and a reviewer can verify the release gates and the boundary to Document Understanding without relying on tribal knowledge.
