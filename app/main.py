"""FastAPI application bootstrap."""

from __future__ import annotations

import logging
import logging.config
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import Settings, get_settings
from app.infrastructure.database.session import create_engine
from app.ingestion.auth import FirebaseAuthVerifier, TokenVerifier
from app.ingestion.errors import (
    AuthenticationError,
    DependencyError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from app.ingestion.registration import DocumentRegistrationService
from app.ingestion.storage import FilesystemArtifactStorage, FirebaseArtifactStorage
from app.ingestion.validation import FileValidator
from app.observability import (
    CorrelationFilter,
    correlation_id,
    metrics,
    new_correlation_id,
    set_correlation_id,
)
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
    correlation_id: str


def configure_logging(settings: Settings | None = None) -> None:
    """Configure application logging once, without request or payload logging."""

    configured = settings or Settings()
    logging.basicConfig(
        level=getattr(logging, configured.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s correlation_id=%(correlation_id)s",
        force=True,
    )
    for handler in logging.getLogger().handlers:
        handler.addFilter(CorrelationFilter())


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API and keep provider orchestration outside route handlers."""

    configured = settings or get_settings()
    configure_logging(configured)
    application = FastAPI(title="Legal Document Intelligence Platform")
    application.state.settings = configured
    application.state.registration_service = None
    application.state.token_verifier = None

    @application.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        request_id = new_correlation_id(request.headers.get("X-Correlation-ID"))
        set_correlation_id(request_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request_id
        return response

    @application.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        detail = (
            exc.detail
            if isinstance(exc.detail, dict)
            else {"code": "http_error", "detail": str(exc.detail)}
        )
        request_id = correlation_id()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": detail.get("code", "http_error"),
                "detail": detail.get("detail", "request failed"),
                "correlation_id": request_id,
            },
            headers={"X-Correlation-ID": request_id},
        )

    @application.exception_handler(RequestValidationError)
    async def request_validation_error_handler(request: Request, exc: RequestValidationError):
        request_id = correlation_id()
        metrics.increment("api_validation_failures")
        return JSONResponse(
            status_code=422,
            content={
                "code": "invalid_request",
                "detail": "request validation failed",
                "correlation_id": request_id,
            },
            headers={"X-Correlation-ID": request_id},
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        logging.getLogger(__name__).exception("unhandled request failure")
        metrics.increment("api_unexpected_failures")
        request_id = correlation_id()
        return JSONResponse(
            status_code=500,
            content={
                "code": "internal_error",
                "detail": "internal server error",
                "correlation_id": request_id,
            },
            headers={"X-Correlation-ID": request_id},
        )

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

    def get_unit_of_work_factory():
        if configured.database_url is None:
            raise DependencyError("document database is not configured")
        service = get_registration_service()
        return service.unit_of_work_factory

    async def owner_from_header(authorization: str | None):
        if not authorization or not authorization.lower().startswith("bearer "):
            raise AuthenticationError("Bearer token is required")
        return (await get_token_verifier().verify(authorization[7:].strip())).owner_id

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

    @application.get("/documents/{document_id}", response_model=DocumentUploadResponse)
    async def get_document(
        document_id: str, authorization: Annotated[str | None, Header()] = None
    ) -> DocumentUploadResponse:
        try:
            owner_id = await owner_from_header(authorization)
            parsed_id = UUID(document_id)
            async with get_unit_of_work_factory()() as unit_of_work:
                document = await unit_of_work.documents.get(parsed_id, owner_id=owner_id)
                if document is None or document.original_artifact_id is None:
                    raise NotFoundError("document was not found")
                artifact = await unit_of_work.artifacts.get(document.original_artifact_id)
                if artifact is None:
                    raise NotFoundError("document original was not found")
                # Job lookup remains explicit and owner-scoped through the document.
                job = await unit_of_work.jobs.get_by_document(parsed_id)
                if job is None:
                    raise NotFoundError("document job was not found")
        except AuthenticationError as exc:
            raise HTTPException(401, {"code": "authentication_failed", "detail": str(exc)}) from exc
        except (ValueError, NotFoundError) as exc:
            raise HTTPException(
                404, {"code": "not_found", "detail": "document was not found"}
            ) from exc
        except DependencyError as exc:
            raise HTTPException(
                503, {"code": "dependency_unavailable", "detail": str(exc)}
            ) from exc
        return DocumentUploadResponse(
            document_id=str(document.document_id),
            original=OriginalMetadataResponse(
                filename=artifact.original_filename,
                mime_type=artifact.mime_type,
                size_bytes=artifact.size_bytes,
                sha256=artifact.sha256,
                storage_reference=artifact.storage_reference,
                uploaded_at=artifact.uploaded_at.isoformat(),
            ),
            uploader_id=document.owner_id,
            uploaded_at=artifact.uploaded_at.isoformat(),
            status=job.status.value,
            job_id=str(job.job_id),
        )

    @application.get("/documents/{document_id}/original")
    async def get_original(document_id: str, authorization: Annotated[str | None, Header()] = None):
        try:
            owner_id = await owner_from_header(authorization)
            parsed_id = UUID(document_id)
            async with get_unit_of_work_factory()() as unit_of_work:
                document = await unit_of_work.documents.get(parsed_id, owner_id=owner_id)
                if document is None or document.original_artifact_id is None:
                    raise NotFoundError("document was not found")
                artifact = await unit_of_work.artifacts.get(document.original_artifact_id)
                if artifact is None:
                    raise NotFoundError("document original was not found")
            data = await get_registration_service().storage.read(artifact.storage_reference)
        except AuthenticationError as exc:
            raise HTTPException(401, {"code": "authentication_failed", "detail": str(exc)}) from exc
        except (ValueError, NotFoundError) as exc:
            raise HTTPException(
                404, {"code": "not_found", "detail": "document was not found"}
            ) from exc
        except StorageError as exc:
            raise HTTPException(
                503,
                {
                    "code": "storage_unavailable",
                    "detail": "original is temporarily unavailable",
                },
            ) from exc
        return StreamingResponse(
            iter([data]),
            media_type=artifact.mime_type,
            headers={"Content-Disposition": f'attachment; filename="{artifact.original_filename}"'},
        )

    return application


app = create_app()
