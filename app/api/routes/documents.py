"""Document HTTP routes; workflows remain in the ingestion service."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.api.auth import AuthenticatedOwner, get_current_user
from app.core.ingestion_errors import (
    AuthenticationError,
    DependencyError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from app.repositories.errors import RepositoryConflict
from app.schemas.documents import DocumentUploadResponse, ErrorResponse, OriginalMetadataResponse


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
    )


def create_document_router(
    *, get_registration_service: Callable, get_token_verifier: Callable, get_uow_factory: Callable
) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/documents",
        response_model=list[DocumentUploadResponse],
        responses={code: {"model": ErrorResponse} for code in (401, 503)},
        summary="List the authenticated user's documents",
    )
    async def list_documents(
        current_user: Annotated[AuthenticatedOwner, Depends(get_current_user)],
        uow_factory=Depends(get_uow_factory),
    ) -> list[DocumentUploadResponse]:
        if uow_factory is None:
            raise HTTPException(
                503,
                {"code": "dependency_unavailable", "detail": "document database is not configured"},
            )
        try:
            async with uow_factory() as unit_of_work:
                documents = await unit_of_work.documents.list(owner_id=current_user.owner_id)
                responses = []
                for document in documents:
                    if document.original_artifact_id is None:
                        continue
                    artifact = await unit_of_work.artifacts.get(document.original_artifact_id)
                    job = await unit_of_work.jobs.get_by_document(document.document_id)
                    if artifact is not None and job is not None:
                        responses.append(_response(document, artifact, job))
                return responses
        except AuthenticationError as exc:
            raise HTTPException(
                401, {"code": "authentication_failed", "detail": "authentication failed"}
            ) from exc
        except DependencyError as exc:
            raise HTTPException(
                503, {"code": "dependency_unavailable", "detail": str(exc)}
            ) from exc

    @router.post(
        "/documents",
        response_model=DocumentUploadResponse,
        responses={code: {"model": ErrorResponse} for code in (400, 401, 409, 413, 422, 503)},
        summary="Upload one document original",
    )
    async def upload_document(
        file: Annotated[UploadFile, File(description="PDF, image, DOCX, or XLSX document")],
        current_user: Annotated[AuthenticatedOwner, Depends(get_current_user)],
        service=Depends(get_registration_service),
    ) -> DocumentUploadResponse:
        try:
            if service is None:
                raise DependencyError("document registration is not configured")
            result = await service.register(
                owner_id=current_user.owner_id,
                filename=file.filename,
                client_mime=file.content_type,
                source=file.file,
            )
        except AuthenticationError as exc:
            raise HTTPException(401, {"code": "authentication_failed", "detail": str(exc)}) from exc
        except ValidationError as exc:
            code = "file_too_large" if "size limit" in str(exc) else "invalid_file"
            raise HTTPException(
                413 if code == "file_too_large" else 422, {"code": code, "detail": str(exc)}
            ) from exc
        except RepositoryConflict as exc:
            raise HTTPException(409, {"code": "conflict", "detail": str(exc)}) from exc
        except StorageError as exc:
            raise HTTPException(503, {"code": "storage_unavailable", "detail": str(exc)}) from exc
        except DependencyError as exc:
            raise HTTPException(
                503, {"code": "dependency_unavailable", "detail": str(exc)}
            ) from exc
        return _response(result.document, result.artifact, result.job)

    @router.get("/documents/{document_id}", response_model=DocumentUploadResponse)
    async def get_document(
        document_id: str,
        current_user: Annotated[AuthenticatedOwner, Depends(get_current_user)],
        uow_factory=Depends(get_uow_factory),
    ) -> DocumentUploadResponse:
        try:
            owner_id = current_user.owner_id
            parsed_document_id = UUID(document_id)
            if uow_factory is None:
                raise DependencyError("document database is not configured")
            async with uow_factory() as unit_of_work:
                document = await unit_of_work.documents.get(parsed_document_id, owner_id=owner_id)
                if document is None or document.original_artifact_id is None:
                    raise NotFoundError("document was not found")
                artifact = await unit_of_work.artifacts.get(document.original_artifact_id)
                job = await unit_of_work.jobs.get_by_document(parsed_document_id)
                if artifact is None or job is None:
                    raise NotFoundError("document metadata was not found")
        except AuthenticationError as exc:
            raise HTTPException(401, {"code": "authentication_failed", "detail": str(exc)}) from exc
        except ValueError, NotFoundError:
            raise HTTPException(404, {"code": "not_found", "detail": "document was not found"})
        except DependencyError as exc:
            raise HTTPException(
                503, {"code": "dependency_unavailable", "detail": str(exc)}
            ) from exc
        return _response(document, artifact, job)

    @router.get("/documents/{document_id}/original")
    async def get_original(
        document_id: str,
        current_user: Annotated[AuthenticatedOwner, Depends(get_current_user)],
        uow_factory=Depends(get_uow_factory),
        service=Depends(get_registration_service),
    ):
        try:
            owner_id = current_user.owner_id
            parsed_document_id = UUID(document_id)
            if uow_factory is None or service is None:
                raise DependencyError("document storage is not configured")
            async with uow_factory() as unit_of_work:
                document = await unit_of_work.documents.get(parsed_document_id, owner_id=owner_id)
                if document is None or document.original_artifact_id is None:
                    raise NotFoundError("document was not found")
                artifact = await unit_of_work.artifacts.get(document.original_artifact_id)
                if artifact is None:
                    raise NotFoundError("document original was not found")
            data = await service.storage.read(artifact.storage_reference)
        except AuthenticationError as exc:
            raise HTTPException(401, {"code": "authentication_failed", "detail": str(exc)}) from exc
        except ValueError, NotFoundError:
            raise HTTPException(404, {"code": "not_found", "detail": "document was not found"})
        except StorageError as exc:
            raise HTTPException(
                503,
                {"code": "storage_unavailable", "detail": "original is temporarily unavailable"},
            ) from exc
        except DependencyError as exc:
            raise HTTPException(
                503, {"code": "dependency_unavailable", "detail": str(exc)}
            ) from exc
        return StreamingResponse(
            iter([data]),
            media_type=artifact.mime_type,
            headers={"Content-Disposition": f'attachment; filename="{artifact.original_filename}"'},
        )

    return router
