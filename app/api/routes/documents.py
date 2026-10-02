"""Document HTTP routes delegating workflows to application services."""

from __future__ import annotations

import base64
from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.auth import AuthenticatedOwner, get_current_user
from app.core.ingestion_errors import DependencyError, NotFoundError
from app.schemas.documents import (
    DocumentDeleteResponse,
    DocumentUploadResponse,
    ErrorResponse,
    OriginalDownloadResponse,
    OriginalMetadataResponse,
)
from app.schemas.responses import ApiResponse, PaginatedData
from app.services.document_management import DocumentManagementService


def _response(document, artifact, job) -> DocumentUploadResponse:
    uploaded_at = artifact.uploaded_at.isoformat()
    return DocumentUploadResponse(
        document_id=str(document.document_id),
        original=OriginalMetadataResponse(
            filename=artifact.original_filename,
            mime_type=artifact.mime_type,
            size_bytes=artifact.size_bytes,
            sha256=artifact.sha256,
            storage_reference=artifact.storage_reference,
            uploaded_at=uploaded_at,
        ),
        uploader_id=document.owner_id,
        uploaded_at=uploaded_at,
        status=job.status.value,
        job_id=str(job.job_id),
        deleted_at=document.deleted_at.isoformat() if document.deleted_at else None,
        deleted_by=document.deleted_by,
    )


def _parse_document_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise NotFoundError("document was not found") from exc


def _management_service_or_error(
    service: DocumentManagementService | None,
) -> DocumentManagementService:
    if service is None:
        raise DependencyError("document database is not configured")
    return service


def create_document_router(
    *, get_registration_service: Callable, get_document_management_service: Callable
) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/documents",
        response_model=ApiResponse[PaginatedData[DocumentUploadResponse]],
        responses={code: {"model": ErrorResponse} for code in (401, 503)},
        summary="List the authenticated user's documents",
    )
    async def list_documents(
        current_user: Annotated[AuthenticatedOwner, Depends(get_current_user)],
        service=Depends(get_document_management_service),
        current_page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
    ) -> ApiResponse[PaginatedData[DocumentUploadResponse]]:
        page = await _management_service_or_error(service).list_documents(
            owner_id=current_user.owner_id,
            current_page=current_page,
            page_size=page_size,
        )
        return ApiResponse(
            data=PaginatedData(
                data=[
                    _response(record.document, record.artifact, record.job)
                    for record in page.records
                ],
                current_page=page.current_page,
                total_data=page.total_data,
                total_page=page.total_page,
            ),
            message="Documents retrieved.",
        )

    @router.post(
        "/documents",
        response_model=ApiResponse[DocumentUploadResponse],
        responses={code: {"model": ErrorResponse} for code in (400, 401, 409, 413, 422, 503)},
        summary="Upload one document original",
    )
    async def upload_document(
        file: Annotated[UploadFile, File(description="PDF, image, DOCX, or XLSX document")],
        current_user: Annotated[AuthenticatedOwner, Depends(get_current_user)],
        service=Depends(get_registration_service),
    ) -> ApiResponse[DocumentUploadResponse]:
        if service is None:
            raise DependencyError("document registration is not configured")
        result = await service.register(
            owner_id=current_user.owner_id,
            filename=file.filename,
            client_mime=file.content_type,
            source=file.file,
        )
        return ApiResponse(
            data=_response(result.document, result.artifact, result.job),
            message="Document uploaded.",
        )

    @router.get("/documents/{document_id}", response_model=ApiResponse[DocumentUploadResponse])
    async def get_document(
        document_id: str,
        current_user: Annotated[AuthenticatedOwner, Depends(get_current_user)],
        service=Depends(get_document_management_service),
    ) -> ApiResponse[DocumentUploadResponse]:
        parsed_document_id = _parse_document_id(document_id)
        record = await _management_service_or_error(service).get_document(
            parsed_document_id, owner_id=current_user.owner_id
        )
        return ApiResponse(
            data=_response(record.document, record.artifact, record.job),
            message="Document retrieved.",
        )

    @router.delete(
        "/documents/{document_id}",
        response_model=ApiResponse[DocumentDeleteResponse],
        responses={code: {"model": ErrorResponse} for code in (401, 404, 503)},
        summary="Hide a document from the owner's list",
    )
    async def delete_document(
        document_id: str,
        current_user: Annotated[AuthenticatedOwner, Depends(get_current_user)],
        service=Depends(get_document_management_service),
    ) -> ApiResponse[DocumentDeleteResponse]:
        parsed_document_id = _parse_document_id(document_id)
        document = await _management_service_or_error(service).delete_document(
            parsed_document_id, owner_id=current_user.owner_id
        )
        return ApiResponse(
            data=DocumentDeleteResponse(
                document_id=str(document.document_id),
                deleted_at=document.deleted_at.isoformat(),
                deleted_by=document.deleted_by,
            ),
            message="Document marked as deleted.",
        )

    @router.get(
        "/documents/{document_id}/original",
        response_model=ApiResponse[OriginalDownloadResponse],
    )
    async def get_original(
        document_id: str,
        current_user: Annotated[AuthenticatedOwner, Depends(get_current_user)],
        service=Depends(get_document_management_service),
    ):
        parsed_document_id = _parse_document_id(document_id)
        original = await _management_service_or_error(service).get_original(
            parsed_document_id, owner_id=current_user.owner_id
        )
        return ApiResponse(
            data=OriginalDownloadResponse(
                filename=original.filename,
                mime_type=original.mime_type,
                size_bytes=len(original.data),
                content_base64=base64.b64encode(original.data).decode("ascii"),
            ),
            message="Original document retrieved.",
        )

    return router
