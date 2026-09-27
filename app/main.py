"""FastAPI application bootstrap."""

from __future__ import annotations

import logging
import logging.config
from typing import Annotated

from fastapi import FastAPI, File, Header, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings, get_settings
from app.infrastructure.database.session import create_engine
from app.ingestion.auth import FirebaseAuthVerifier, TokenVerifier
from app.ingestion.errors import AuthenticationError, StorageError, ValidationError
from app.ingestion.registration import DocumentRegistrationService
from app.ingestion.storage import FilesystemArtifactStorage, FirebaseArtifactStorage
from app.ingestion.validation import FileValidator
from app.repositories.errors import RepositoryConflict
from app.repositories.sqlalchemy import SqlAlchemyMetadataUnitOfWork


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


def configure_logging(settings: Settings | None = None) -> None:
    """Configure application logging once, without request or payload logging."""

    configured = settings or Settings()
    logging.basicConfig(
        level=getattr(logging, configured.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API and keep provider orchestration outside route handlers."""

    configured = settings or get_settings()
    configure_logging(configured)
    application = FastAPI(title="Legal Document Intelligence Platform")
    application.state.settings = configured
    application.state.registration_service = None
    application.state.token_verifier = None

    @application.get("/health", response_model=dict[str, str])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    def get_registration_service() -> DocumentRegistrationService:
        if application.state.registration_service is None:
            if configured.database_url is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="document registration is not configured",
                )
            engine = create_engine(configured)
            factory = async_sessionmaker(engine, expire_on_commit=False)
            storage = (
                FirebaseArtifactStorage(configured.firebase_storage_bucket)
                if configured.storage_backend == "firebase" and configured.firebase_storage_bucket
                else FilesystemArtifactStorage(configured.storage_root)
            )
            application.state.registration_service = DocumentRegistrationService(
                validator=FileValidator(configured),
                storage=storage,
                unit_of_work_factory=lambda: SqlAlchemyMetadataUnitOfWork(factory),
                routing_key=configured.rabbitmq_routing_key,
            )
        return application.state.registration_service

    def get_token_verifier() -> TokenVerifier:
        if application.state.token_verifier is None:
            application.state.token_verifier = FirebaseAuthVerifier()
        return application.state.token_verifier

    @application.post(
        "/documents",
        response_model=DocumentUploadResponse,
        responses={
            400: {"model": ErrorResponse},
            401: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            413: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
        summary="Upload one document original",
    )
    async def upload_document(
        file: Annotated[UploadFile, File(description="PDF, image, DOCX, or XLSX document")],
        authorization: Annotated[str | None, Header()] = None,
    ) -> DocumentUploadResponse:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=401,
                detail={"code": "authentication_required", "detail": "Bearer token is required"},
            )
        try:
            verifier = get_token_verifier()
            owner = await verifier.verify(authorization[7:].strip())
            service = get_registration_service()
            result = await service.register(
                owner_id=owner.owner_id,
                filename=file.filename,
                client_mime=file.content_type,
                source=file.file,
            )
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=401, detail={"code": "authentication_failed", "detail": str(exc)}
            ) from exc
        except ValidationError as exc:
            code = "file_too_large" if "size limit" in str(exc) else "invalid_file"
            status_code = 413 if code == "file_too_large" else 422
            raise HTTPException(
                status_code=status_code, detail={"code": code, "detail": str(exc)}
            ) from exc
        except RepositoryConflict as exc:
            raise HTTPException(
                status_code=409, detail={"code": "conflict", "detail": str(exc)}
            ) from exc
        except StorageError as exc:
            raise HTTPException(
                status_code=503, detail={"code": "storage_unavailable", "detail": str(exc)}
            ) from exc

        return DocumentUploadResponse(
            document_id=str(result.document.document_id),
            original=OriginalMetadataResponse(
                filename=result.artifact.original_filename,
                mime_type=result.artifact.mime_type,
                size_bytes=result.artifact.size_bytes,
                sha256=result.artifact.sha256,
                storage_reference=result.artifact.storage_reference,
                uploaded_at=result.artifact.uploaded_at.isoformat(),
            ),
            uploader_id=result.document.owner_id,
            uploaded_at=result.artifact.uploaded_at.isoformat(),
            status=result.job.status.value,
            job_id=str(result.job.job_id),
        )

    return application


app = create_app()
