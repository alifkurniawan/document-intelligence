# Phase 17 — Implementation Plan

This plan is a draft task-group sequence. Items marked as decision-dependent must
be finalized in `requirements.md` before implementation begins.

1. **Finalize the feature contract**
   - Confirm supported formats, first-release processor policy, representation
     minimum, semantic extraction scope, persistence choices, and operational SLOs.
   - Record decisions and non-goals in `requirements.md`.
   - Define stable input/output contracts without coupling them to a provider SDK.

2. **Define processing and provenance models**
   - Model inspection results, processor selection, processing versions, status,
     failures, retry metadata, representations, and source provenance.
   - Preserve the distinction between original artifact, intermediate output,
     structural representation, and semantic result.
   - Add focused unit tests for invariants and invalid transitions.

3. **Implement original-artifact access and processor selection**
   - Resolve the persisted artifact reference through the storage boundary.
   - Inspect characteristics and select the simplest appropriate processor.
   - Add deterministic behavior for unsupported formats and unavailable processors.

4. **Implement format processors**
   - Add only the approved PDF, image/OCR, DOCX, and XLSX paths.
   - Keep PaddleOCR-specific behavior behind an injectable processor boundary.
   - Capture processor and dependency versions needed for reproducibility.
   - Test valid, malformed, empty, and processor-failure inputs.

5. **Build Document Representation and provenance**
   - Produce the agreed representation for content and observable structure.
   - Attach source references such as artifact/version, page or block, coordinates,
     source text, processor version, and processing timestamp where applicable.
   - Verify that derived data cannot mutate or replace the original artifact.

6. **Integrate asynchronous execution and lifecycle**
   - Consume the existing reference-only job contract.
   - Persist processing status and outcomes with safe acknowledgements and bounded
     retry/dead-letter behavior.
   - Add explicit reprocessing from an existing original artifact.

7. **Add semantic extraction if approved**
   - Run semantic extraction only against the representation.
   - Use the approved taxonomy and version the applicable model, prompt, or logic.
   - Keep semantic failures and results separate from structural processing state.

8. **Verify end-to-end behavior and operational readiness**
   - Add unit, integration, and API/worker tests for happy paths, ownership,
     retries, permanent failures, reprocessing, provenance, and immutability.
   - Update documentation, configuration examples, runbooks, and release notes.
   - Execute the checks in `validation.md` before merge.
