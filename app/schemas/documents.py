"""HTTP request and response contracts for documents."""

from pydantic import BaseModel


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


class ErrorResponse(BaseModel):
    code: str
    detail: str
    correlation_id: str


__all__ = ["DocumentUploadResponse", "ErrorResponse", "OriginalMetadataResponse"]
