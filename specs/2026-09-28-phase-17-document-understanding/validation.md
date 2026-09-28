# Phase 17 — Validation and Merge Criteria

The feature is ready to merge only when the approved scope is implemented and the
following evidence is available.

## Contract and architecture

- The implementation consumes an existing original artifact by reference and does
  not require a new upload.
- Processor selection follows documented document characteristics and the simplest
  appropriate method.
- OCR is replaceable and is not forced onto formats that do not require it.
- Provider-specific dependencies remain behind meaningful application boundaries.
- No binary document content is stored in PostgreSQL or sent through RabbitMQ.

## Representation and provenance

- Every successful result contains the agreed content and observable-structure
  fields.
- Provenance is retained at the practical granularity supported by each processor.
- Results identify the relevant processor/engine and logic/model/prompt versions,
  plus processing time where applicable.
- Intermediate and derived outputs remain distinct from the immutable original.

## Reliability and lifecycle

- Processing states, retry limits, acknowledgement behavior, and permanent failure
  reporting are deterministic and tested.
- A failed or retried job cannot overwrite the original or publish an unusable
  reference.
- Reprocessing can create a new versioned result from the same original artifact.
- Ownership and authorization rules prevent cross-account access.

## Test and quality checks

- Unit tests cover processor selection, representation invariants, provenance,
  failure mapping, and state transitions.
- Integration tests cover storage access, persistence, RabbitMQ hand-off, retry,
  and reprocessing using isolated infrastructure or approved test doubles.
- API/worker tests cover the agreed request or trigger contract and observable
  status/failure responses.
- `pytest` passes, Ruff checks and formatting pass, and migrations are tested if
  schema changes are introduced.
- Documentation describes supported formats, configuration, operational recovery,
  and the boundary between ingestion and understanding.

## Merge evidence

The pull request includes the finalized requirements decisions, test command output,
any migration/rollback notes, known limitations, and confirmation that all explicit
non-goals remain out of scope.
