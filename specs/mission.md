# Mission

## Project mission

Build a dependable, asynchronous Document Ingestion subsystem that accepts an authenticated user's document, validates it, preserves the uploaded original, records its metadata, creates a downstream processing job, and reports the resulting document and processing status.

## Problem being solved

External documents need a consistent entry point into the platform with clear ownership, validation, durable provenance, and a reliable hand-off to downstream processing. The ingestion boundary must make the original file reproducible while remaining independent of any particular upload channel or downstream intelligence implementation.

## System purpose and scope

The system is a pragmatic modular monolith for Document Ingestion. It supports a core ingestion service that can be called by web upload, batch-upload, and import adapters. The core workflow is:

1. Authenticate and authorize the user.
2. Accept and validate the input.
3. Register a logical document and its metadata.
4. Persist the original artifact immutably.
5. Create an asynchronous processing job containing references, not file bytes.
6. Return the document information and processing status without waiting for downstream processing.

The initial supported formats are PDF, scanned PDF, JPEG, PNG, other explicitly allowlisted image formats, DOCX, and XLSX. A scanned PDF remains an input artifact; ingestion does not perform OCR.

## Non-goals and boundary

Document Ingestion explicitly does **not** perform Document Understanding. It must not implement or require OCR, VLM/LLM understanding, classification, entity extraction, clause extraction, obligation extraction, semantic analysis, embeddings, RAG, legal analysis, or Shariah analysis. These belong to downstream systems.

Normalization is optional and technical only. It may read basic properties, determine page count when reliable, or produce technical metadata needed by a downstream processor. It must not infer document meaning, and it must not convert every input into another physical format without a concrete requirement. A Canonical Document Representation is not mandatory; the original artifact plus metadata is the default design.

## Document and Artifact

* **Document** is the logical record registered in the platform and identified by a unique `document_id`.
* **Artifact** is a physical file associated with a document. The initial artifact is the uploaded original; future technical derivatives may be added without replacing it.

The original artifact is the source of truth. It must remain independently available and reproducible regardless of normalization, processing results, OCR results, or AI-generated results.

## Original-artifact policy

Original files are immutable and must never be overwritten. The system stores the original outside PostgreSQL, while PostgreSQL stores metadata and a storage reference. At minimum, metadata includes the original filename, MIME type, size, SHA-256 hash, storage URI/reference, upload time, and authenticated uploader. Object paths should be uniquely scoped to the document and original artifact; retries must not replace an existing original silently.

Binary contents must not be stored in PostgreSQL or placed in RabbitMQ messages. RabbitMQ messages contain identifiers such as `document_id` and `job_id`, plus the minimum execution metadata required by the consumer.

## Ingestion lifecycle

The lifecycle is `received -> validating -> registered/stored -> queued`, followed by downstream-owned states `processing`, `completed`, or `failed`. Exact persistence transitions and recovery behavior are defined by feature specifications and must preserve the invariant that a job cannot instruct a consumer to read an uncommitted or missing original artifact.

The single-document upload workflow is the first MVP path. Batch and import are adapters that invoke the same core service rather than separate business workflows.

## Core engineering principles

1. Preserve provenance: the original artifact is immutable source of truth.
2. Keep ingestion separate from understanding.
3. Make long-running work asynchronous; upload responses do not wait for processing.
4. Prefer a simple, modular, testable monolith over premature microservices.
5. Isolate domain/application logic from PostgreSQL, RabbitMQ, Firebase, and storage providers where practical.
6. Keep abstractions proportional to current requirements; document architecture decisions.
7. Load credentials, connection strings, and configuration from environment variables; never hard-code secrets.
8. Validate type, extension, size, readability/integrity, and appropriate basic format properties before acceptance.
9. Make retries safe and observable without overcomplicating the first implementation.

## Important invariants

* Every accepted document has one unique `document_id` and an authenticated owner.
* An accepted original has verifiable filename, MIME type, size, SHA-256, and storage reference metadata.
* The original artifact cannot be overwritten by normalization or processing.
* PostgreSQL contains metadata, not document binaries.
* RabbitMQ contains job references, not document binaries.
* A processing job is created only after the document and original-artifact metadata can be durably resolved.
* A user can operate only on documents allowed for that account; the initial authorization model is account ownership.
* Downstream processing can be retried from the original artifact.

## Definition of Done

The ingestion subsystem is done when an authenticated user can upload each supported input through the core API, receive deterministic validation errors for unsupported or invalid files, obtain a durable document and original-artifact record, retrieve the immutable original through its storage reference, observe a queued asynchronous job, and see safe failure/retry behavior. Automated unit, integration, and API tests cover the workflow and invariants; migrations, configuration, operational documentation, and explicit boundaries to Document Understanding are documented.
