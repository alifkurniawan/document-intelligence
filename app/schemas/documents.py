"""HTTP request and response contracts for documents."""

from pydantic import BaseModel

from app.schemas.responses import ErrorResponse


class OriginalMetadataResponse(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    storage_reference: str
    uploaded_at: str


class DocumentUploadResponse(BaseModel):
    document_id: str
    original: OriginalMetadataResponse
    uploader_id: str
    uploaded_at: str
    status: str
    job_id: str
    deleted_at: str | None = None
    deleted_by: str | None = None


class DocumentDeleteResponse(BaseModel):
    document_id: str
    deleted_at: str
    deleted_by: str


class OriginalDownloadResponse(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int
    content_base64: str


__all__ = [
    "DocumentDeleteResponse",
    "DocumentUploadResponse",
    "ErrorResponse",
    "OriginalDownloadResponse",
    "OriginalMetadataResponse",
]
