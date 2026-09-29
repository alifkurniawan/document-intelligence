# Mission

## Project mission

Build a dependable, asynchronous Document Intelligence platform that accepts an authenticated user's document, preserves the uploaded original through Document Ingestion, and provides Document Understanding as the next processing capability for producing a traceable representation of document content and structure.

## Problem being solved

External documents need a consistent entry point into the platform with clear ownership, validation, durable provenance, and a reliable hand-off to processing. The ingestion boundary must make the original file reproducible while remaining independent of any particular upload channel or downstream intelligence implementation. Document Understanding must make the observable content and structure of that immutable source usable by later capabilities without obscuring its origin.

## System purpose and scope

The system is a pragmatic modular monolith for Document Ingestion and Document Understanding. The current backend is organized into an HTTP/API layer, shared core configuration and infrastructure helpers, provider-neutral models, application services, persistence repositories, artifact storage adapters, and background workers. Web upload, batch-upload, and import adapters are entry points to the same core ingestion service. The platform workflow is:

1. Authenticate and authorize the user.
2. Accept and validate the input.
3. Register a logical document and its metadata.
4. Persist the original artifact immutably.
5. Create an asynchronous processing job containing references, not file bytes.
6. Return the document information and processing status without waiting for downstream processing.

After ingestion, Document Understanding consumes the immutable original artifact through its reference and performs document inspection, processor selection, content extraction, OCR when required, structure and layout analysis, Document Representation construction, provenance capture, and semantic extraction. The resulting relationship is:

```text
Document Ingestion
        ↓
Original Artifact
        ↓
Document Understanding
        ↓
Document Representation
        ↓
Semantic Information
        ↓
Future Downstream Intelligence
```

The initial supported formats are PDF, scanned PDF, JPEG, PNG, other explicitly allowlisted image formats, DOCX, and XLSX. A scanned PDF remains an input artifact; ingestion does not perform OCR.

## Non-goals and boundary

Document Ingestion owns receiving, authentication and authorization, basic validation, document registration, document ID and metadata, immutable original-artifact storage, processing-job creation, and asynchronous hand-off. It does not perform Document Understanding. Document Understanding is a subsequent processing capability and owns document processing, structure, representation, and semantic extraction. It must not replace or modify the original artifact.

Document Understanding does not include embeddings, RAG, question answering, document comparison, legal reasoning or analysis, Shariah analysis, legal risk analysis, recommendations, or autonomous agents. These remain future or downstream concerns.

Technical normalization is optional and only justified by a concrete compatibility need. It must not replace the original artifact or infer document meaning. Document Understanding may produce intermediate data such as OCR results, extracted text, page images, layout information, and parsed structure, but intermediate data, the original artifact, and derived semantic data remain distinct. A detailed storage schema is not prescribed here.

## Document and Artifact

* **Document** is the logical record registered in the platform and identified by a unique `document_id`.
* **Artifact** is a physical file associated with a document. The initial artifact is the uploaded original; future technical derivatives may be added without replacing it.

The original artifact is the source of truth. It must remain independently available and reproducible regardless of normalization, processing results, OCR results, or AI-generated results.

## Document Understanding principles

Document Understanding uses the simplest appropriate processing method for the document. The system inspects document characteristics before selecting a processor. Typical choices include a PDF/text parser for text PDFs, OCR for scanned PDFs and images, a DOCX parser for DOCX, and a spreadsheet parser for XLSX. No document is required to pass through OCR, a VLM, or an LLM when a simpler or specialized processor is adequate.

OCR is a first-class document-processing capability. PaddleOCR is the preferred initial OCR implementation, while the architecture remains independent of PaddleOCR-specific details so the engine can evolve when requirements justify another implementation. OCR is not replaced by VLM or LLM processing by default. VLM/LLM use is optional and requires a concrete requirement that simpler or specialized processing cannot adequately address.

Document Representation is the structured, machine-readable representation of a document's content and observable structure. It may include document information, pages, text blocks, headings, paragraphs, tables, images, reading order, layout and positional information, and provenance. It is an architectural responsibility rather than a prescribed database schema.

Document structure describes what physically or structurally exists: pages, text, blocks, headings, paragraphs, tables, images, coordinates, layout, and reading order. Semantic information describes what the content means: people, organizations, addresses, dates, monetary amounts, property, clauses, obligations, and relationships. Semantic extraction operates on the Document Representation and never modifies the original artifact.

Derived information remains traceable to its source whenever practical. Provenance may refer to the document, artifact or version, page, block, bounding box, source text, processor and processor version, model and model version, prompt version, extraction-logic version, and processing timestamp as applicable to the method. Traceability is required; a rigid set of fields for every processing method is not.

Document Understanding processing is version-aware. Results are associated with the applicable processing configuration, and an immutable original artifact can be reprocessed when processors, OCR engines, models, prompts, or extraction logic change without requiring the user to upload the artifact again.

## Document Understanding constitution

Document Understanding covers every format supported by Document Ingestion: PDF,
scanned PDF, images such as JPEG and PNG, DOCX, and XLSX. Implementation may be
incremental, but the architecture must not restrict the capability to a subset of
these formats. Processor selection is based on document characteristics: text-based
PDFs use a PDF/text parser, scanned PDFs and images use OCR, DOCX uses a DOCX parser,
and XLSX uses a spreadsheet parser. Formats do not share a mandatory universal
pipeline.

Semantic extraction is part of Document Understanding at a generic,
document-level scope. Initial results may include persons, organizations, addresses,
dates, monetary amounts, document identifiers, generic clauses, generic obligations,
and relationships. Legal or Shariah ontologies, reasoning, interpretation, risk
analysis, and other domain-specific intelligence are downstream capabilities and
are not introduced here.

The minimum Document Representation must provide downstream consumers with text,
structure, location, and provenance without requiring them to reprocess the original
artifact. Conceptually, it supports a document identifier, artifact reference,
pages with page numbers and dimensions, content blocks with block type and text,
bounding boxes or positional information where available, reading order where
available, tables, images, and provenance. This is a capability contract rather
than an unnecessarily rigid or complex database schema.

Persistence follows the existing architecture. Firebase Storage holds original
artifacts and large intermediate or derived artifacts such as OCR output and page
images when appropriate. PostgreSQL holds document metadata, processing status and
jobs, Document Representation metadata and structured content, semantic extraction
results, provenance, and processing/version metadata. Large binary artifacts are
never stored directly in PostgreSQL. The original artifact remains immutable and
authoritative; representations and semantic results are derived, versioned, and
reproducible from it.

## Original-artifact policy

Original files are immutable and must never be overwritten. The system stores the original outside PostgreSQL, while PostgreSQL stores metadata and a storage reference. At minimum, metadata includes the original filename, MIME type, size, SHA-256 hash, storage URI/reference, upload time, and authenticated uploader. Object paths should be uniquely scoped to the document and original artifact; retries must not replace an existing original silently.

Binary contents must not be stored in PostgreSQL or placed in RabbitMQ messages. RabbitMQ messages contain identifiers such as `document_id` and `job_id`, plus the minimum execution metadata required by the consumer.

## Ingestion lifecycle

The lifecycle is `received -> validating -> registered/stored -> queued`, followed by downstream-owned states `processing`, `completed`, or `failed`. Exact persistence transitions and recovery behavior are defined by feature specifications and must preserve the invariant that a job cannot instruct a consumer to read an uncommitted or missing original artifact.

The single-document upload workflow is the first MVP path. Batch and import are adapters that invoke the same core service rather than separate business workflows.

Authenticated users may list their own registered documents through the API. Listing
is owner-scoped, returns newest documents first, and exposes metadata and processing
status without returning original bytes. It must not reveal documents belonging to
another account.

## Current module boundaries

The Python package is intentionally split by responsibility:

* `app/api` owns FastAPI bootstrap, routes, authentication integration, and HTTP error mapping.
* `app/core` owns settings, database engine/session setup, Firebase initialization, observability, and shared errors.
* `app/models` owns provider-neutral entities and SQLAlchemy persistence models.
* `app/services` owns validation, ingestion orchestration, and recovery workflows.
* `app/repositories` owns database repository implementations and the metadata unit of work.
* `app/storage` owns artifact-storage ports and filesystem/Firebase implementations.
* `app/workers` owns processing contracts, RabbitMQ publishing, outbox dispatch, and worker runtime.
* `app/schemas` owns API request/response models.

These are package boundaries inside one deployable backend, not separate services. The API process and outbox worker use the same application package and database contracts.

## Core engineering principles

1. Preserve provenance: the original artifact is immutable source of truth.
2. Keep ingestion separate from understanding.
3. Use the simplest appropriate processing method, preserve the relationship to the source document, and use AI models only where they provide concrete value.
4. Make long-running work asynchronous; upload responses do not wait for processing.
5. Prefer a simple, modular, testable monolith over premature microservices.
6. Isolate provider-specific code behind the API, repository, storage, authentication, and worker boundaries where practical.
7. Keep abstractions proportional to current requirements; document architecture decisions.
8. Use Dependency Injection for application services and processing components so they remain testable and maintainable; Dependency Injection does not require unnecessary Dependency Abstraction.
9. Load credentials, connection strings, and configuration from environment variables; never hard-code secrets.
10. Validate type, extension, size, readability/integrity, and appropriate basic format properties before acceptance.
11. Make retries safe and observable without overcomplicating the first implementation.

## Important invariants

* Every accepted document has one unique `document_id` and an authenticated owner.
* An accepted original has verifiable filename, MIME type, size, SHA-256, and storage reference metadata.
* The original artifact cannot be overwritten by normalization or processing.
* PostgreSQL contains metadata, not document binaries.
* RabbitMQ contains job references, not document binaries.
* A processing job is created only after the document and original-artifact metadata can be durably resolved.
* A user can operate only on documents allowed for that account; the initial authorization model is account ownership.
* Document listings are owner-scoped and never disclose another account's documents.
* Downstream processing can be retried from the original artifact.
* Document Understanding processing has observable status and supports retry, permanent failure reporting, and reprocessing.
* Intermediate processing data and derived semantic data never replace the original artifact.

## Definition of Done

The ingestion and understanding foundation is done when an authenticated user can upload each supported input through the core API, receive deterministic validation errors for unsupported or invalid files, obtain a durable document and original-artifact record, retrieve the immutable original through its storage reference, observe a queued asynchronous job, and see safe failure/retry behavior. Document Understanding must be able to inspect the original, select an appropriate processor, produce a traceable Document Representation, and optionally derive semantic information without changing the original. Automated unit, integration, and API tests cover the workflow and invariants; implementation-specific processing behavior belongs in a future feature specification.
