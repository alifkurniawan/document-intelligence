# API contract

The API is served by `app.api.app:app`. Interactive OpenAPI documentation is available at
`/docs` when the service is running. All document routes require an application access
token in `Authorization: Bearer <token>`; Firebase ID tokens are used only at exchange.

## Endpoints

All JSON responses use `{ "data": ..., "message": "..." }`. Errors use the same
outer envelope, with `data` containing `code` and `correlation_id` and `message`
containing the human-readable error.

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/health` | Liveness check; no authentication | `200 ApiResponse` |
| POST | `/auth/token` | Exchange a verified Firebase ID token | `200 ApiResponse<AccessTokenResponse>` |
| POST | `/auth/refresh` | Rotate a refresh session and issue new tokens | `200 ApiResponse<AccessTokenResponse>` |
| POST | `/auth/logout` | Revoke a refresh session | `200 ApiResponse` |
| POST | `/documents` | Register one authenticated original | `200 ApiResponse<DocumentUploadResponse>` |
| GET | `/documents` | List the authenticated user's documents | `200 ApiResponse<PaginatedData<DocumentUploadResponse>>` |
| GET | `/documents/{document_id}` | Read owner-scoped metadata and job status | `200 ApiResponse<DocumentUploadResponse>` |
| DELETE | `/documents/{document_id}` | Hide an owned document from the list (soft delete) | `200 ApiResponse<DocumentDeleteResponse>` |
| GET | `/documents/{document_id}/original` | Read the owner-scoped immutable original | `200 ApiResponse<OriginalDownloadResponse>` |

### List pagination

`GET /documents` accepts `current_page` (default `1`) and `page_size` (default `20`,
maximum `100`). The response shape is:

```json
{
  "data": {
    "data": [],
    "current_page": 1,
    "total_data": 0,
    "total_page": 0
  },
  "message": "Documents retrieved."
}
```

### Upload

Submit `multipart/form-data` with one field named `file`. The filename must be a
simple filename without path separators or NUL bytes. The service validates the
content-derived MIME type, extension, size, readability, and format integrity before
writing metadata. The default limit is 25 MiB (`MAX_UPLOAD_SIZE_BYTES`).

Example:

```shell
curl -X POST http://127.0.0.1:8000/documents \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@contract.pdf"
```

The `data` object contains string UUIDs for `document_id` and `job_id`, the authenticated
`uploader_id`, `status` (`queued` on successful registration), timestamps, and
`original` metadata: `filename`, `mime_type`, `size_bytes`, `sha256`,
`storage_reference`, and `uploaded_at`. Upload returns after durable registration and
does not wait for downstream processing.

### Status and original retrieval

Use `data.document_id` with the same owner's token. A document lookup returns the same
metadata shape and current job status under `data`. The original endpoint returns
`filename`, `mime_type`, `size_bytes`, and `content_base64` under `data`; decode the
Base64 field to recover the stored bytes. It never returns a derivative or processing
result.

Ownership is enforced by querying with the authenticated application user ID. A document
owned by another account is indistinguishable from a missing document and returns
`404`.

### Soft delete and audit

`DELETE /documents/{document_id}` marks the document as deleted; it does not remove
the original file or metadata. Marked documents no longer appear in `GET /documents`.
The delete response's `data` contains `deleted_at` and `deleted_by`, where `deleted_by` is the
authenticated application user ID. Repeating the request returns the original marker,
so the first deleting user and timestamp remain recorded. Owner-scoped detail reads
include these fields to support audit tracking.

### Authentication lifecycle

The client authenticates with Firebase, exchanges the Firebase ID token at
`POST /auth/token`, and uses `data.access_token` from the response for API calls. When
needed, `POST /auth/refresh` validates and rotates the independently stored refresh
session. `POST /auth/logout` revokes that session; it does not sign the user out of
Firebase. Authentication failures return `401`, while disabled application users return
`403`. Token lifetimes are configurable with `ACCESS_TOKEN_EXPIRE_SECONDS` and
`REFRESH_TOKEN_EXPIRE_SECONDS`.

### Errors

Errors use:

```json
{"data":{"code":"invalid_file","correlation_id":"..."},"message":"..."}
```

The service maps common failures as follows:

| Status | Codes / meaning |
| --- | --- |
| 401 | `authentication_required`, `authentication_failed` |
| 403 | `user_disabled`, `forbidden` |
| 404 | `not_found` for invalid, missing, or unauthorized document IDs |
| 409 | `conflict` or `invalid_state_transition` |
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
