# API contract

The API is served by `app.api.app:app`. Interactive OpenAPI documentation is available at
`/docs` when the service is running. All document routes require a Firebase ID token
in `Authorization: Bearer <token>`.

## Endpoints

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/health` | Liveness check; no authentication | `200 {"status":"ok"}` |
| POST | `/documents` | Register one authenticated original | `200 DocumentUploadResponse` |
| GET | `/documents/{document_id}` | Read owner-scoped metadata and job status | `200 DocumentUploadResponse` |
| GET | `/documents/{document_id}/original` | Stream the owner-scoped immutable original | `200` with the stored MIME type |

### Upload

Submit `multipart/form-data` with one field named `file`. The filename must be a
simple filename without path separators or NUL bytes. The service validates the
content-derived MIME type, extension, size, readability, and format integrity before
writing metadata. The default limit is 25 MiB (`MAX_UPLOAD_SIZE_BYTES`).

Example:

```shell
curl -X POST http://127.0.0.1:8000/documents \
  -H "Authorization: Bearer $FIREBASE_ID_TOKEN" \
  -F "file=@contract.pdf"
```

The response contains string UUIDs for `document_id` and `job_id`, the authenticated
`uploader_id`, `status` (`queued` on successful registration), timestamps, and
`original` metadata: `filename`, `mime_type`, `size_bytes`, `sha256`,
`storage_reference`, and `uploaded_at`. Upload returns after durable registration and
does not wait for downstream processing.

### Status and original retrieval

Use the returned `document_id` with the same owner's token. A document lookup returns
the same metadata shape and the current job status. The original endpoint returns the
stored bytes with `Content-Type` matching the validated MIME type and an attachment
filename. It never returns a derivative or processing result.

Ownership is enforced by querying with the authenticated Firebase UID. A document
owned by another account is indistinguishable from a missing document and returns
`404`.

### Errors

Except for the successful binary original response, errors use:

```json
{"code":"invalid_file","detail":"...","correlation_id":"..."}
```

The service maps common failures as follows:

| Status | Codes / meaning |
| --- | --- |
| 401 | `authentication_required`, `authentication_failed` |
| 404 | `not_found` for invalid, missing, or unauthorized document IDs |
| 409 | `conflict` when an immutable original or metadata constraint conflicts |
| 413 | `file_too_large` |
| 422 | `invalid_file` or `invalid_request` |
| 503 | `storage_unavailable`, `dependency_unavailable`, or unconfigured registration |
| 500 | `internal_error` |

Every response includes `X-Correlation-ID`. A client may supply a safe correlation ID;
the server returns the value it accepted and includes it in the public error envelope.

## Supported inputs

The default allowlist is PDF (`.pdf`, `application/pdf`), JPEG (`.jpg`/`.jpeg`,
`image/jpeg`), PNG (`.png`, `image/png`), DOCX (`.docx`, the Office Open XML document
MIME), and XLSX (`.xlsx`, the Office Open XML spreadsheet MIME). A scanned PDF is
accepted as a PDF; no OCR is performed. Content detection is authoritative, so a
client-declared MIME mismatch or extension/content mismatch is rejected.

Adding a format requires an explicit allowlist/configuration decision, content
detection and integrity checks in `FileValidator`, storage/retrieval coverage, focused
tests, and updates to this table and `.env.example`. Do not weaken original
immutability or add semantic extraction as part of format support.
