# Phase 17 — Document Understanding

## Status

Feature decisions finalized. Implementation may proceed incrementally, provided
the architecture supports the complete ingestion format set and the contracts below.

## Context

Document Ingestion now preserves an authenticated user's original artifact and
hands off a reference asynchronously. This feature consumes that immutable original
by reference and produces a traceable, machine-readable Document Representation.
The original artifact remains the source of truth and is never modified or
replaced.

The feature follows the guidance in `specs/mission.md`, `specs/roadmap.md`, and
`specs/tech-stack.md`: keep understanding separate from ingestion, use the
simplest appropriate processor, keep OCR replaceable, preserve provenance, and
avoid speculative services or abstractions.

## Scope

The implementation should define and implement the smallest reviewable slice of:

1. Loading an existing original artifact from its persisted reference.
2. Inspecting document characteristics and selecting an appropriate processor.
3. Extracting content for the supported formats in the selected slice.
4. Performing OCR only when required by the document characteristics and agreed
   processor policy.
5. Capturing observable structure such as pages, blocks, reading order, tables,
   images, and positional data where available.
6. Producing a version-aware Document Representation with practical provenance.
7. Recording processing status, bounded retry, failure reporting, and reprocessing
   from the existing original without a new upload.
8. Performing generic document-level semantic extraction for persons,
   organizations, addresses, dates, monetary amounts, document identifiers,
   generic clauses, generic obligations, and relationships.

## Finalized decisions

- Original artifacts are immutable and remain outside PostgreSQL.
- RabbitMQ messages contain references and execution metadata, never binary data.
- The implementation remains inside the existing modular monolith.
- Processing components use dependency injection at meaningful boundaries.
- Text/PDF parsing, OCR, DOCX parsing, and XLSX parsing are selected by document
  characteristics; OCR is not mandatory for every input.
- PaddleOCR is the preferred initial OCR implementation, behind a replaceable
  processing boundary.
- All ingestion-supported formats are in the capability contract: PDF, scanned PDF,
  images such as JPEG and PNG, DOCX, and XLSX. The implementation may be
  incremental but must not architecturally restrict the capability to a subset.
- Processor selection is characteristic-driven: text-based PDF to PDF/text parser,
  scanned PDF and images to OCR, DOCX to DOCX parser, and XLSX to spreadsheet
  parser. A universal pipeline is not required.
- Semantic extraction is generic/document-level only. Legal or Shariah ontology,
  reasoning, interpretation, risk analysis, and other domain-specific intelligence
  remain downstream capabilities.
- The minimum representation contract is conceptually document identifier, artifact
  reference, pages with number and dimensions, content blocks with type and text,
  positional information where available, reading order where available, tables,
  images, and provenance. The contract is not a rigid database schema.
- Firebase Storage stores original artifacts and large intermediate/derived files
  when appropriate. PostgreSQL stores metadata, processing/jobs, representation
  metadata and structured content, semantic results, provenance, and
  processing/version metadata. Large binaries are not stored in PostgreSQL.
- Representations and semantic results are derived, reproducible, and reprocessable
  from the immutable original artifact.
- VLM/LLM processing, RAG, vector search, question answering, legal analysis, and
  autonomous agents are out of scope unless this specification is explicitly
  narrowed or expanded by decision.

## Remaining implementation decisions

- Which format processor is implemented first within the complete capability
  contract?
- Which processing states, retry limits, and reprocessing trigger/API are required?
- What accuracy, latency, and resource limits determine acceptance for each initial
  processor path?

## Out of scope

RAG, embeddings/vector search, question answering, comparison, legal reasoning or
analysis, Shariah analysis, legal risk analysis, recommendations, and autonomous
agents. No implementation may overwrite the original artifact.
