"""Central HTTP error mapping for API and application exceptions."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import DomainError, InvalidStateTransition, OwnershipError
from app.core.ingestion_errors import (
    AuthenticationError,
    AuthorizationError,
    DependencyError,
    NotFoundError,
    StorageError,
    ValidationError,
)
from app.core.observability import correlation_id, metrics
from app.repositories.errors import RepositoryConflict

logger = logging.getLogger(__name__)


def _error_response(
    status_code: int,
    code: str,
    detail: str,
    *,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = correlation_id()
    response_headers = dict(headers or {})
    response_headers["X-Correlation-ID"] = request_id
    return JSONResponse(
        status_code=status_code,
        content={
            "data": {"code": code, "correlation_id": request_id},
            "message": detail,
        },
        headers=response_headers,
    )


async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = (
        exc.detail
        if isinstance(exc.detail, dict)
        else {"code": "http_error", "detail": str(exc.detail)}
    )
    return _error_response(
        exc.status_code,
        detail.get("code", "http_error"),
        detail.get("detail", "request failed"),
        headers=exc.headers,
    )


async def request_validation_exception_handler(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    metrics.increment("api_validation_failures")
    return _error_response(422, "invalid_request", "request validation failed")


async def authentication_exception_handler(
    _request: Request, exc: AuthenticationError
) -> JSONResponse:
    detail = str(exc)
    code = "authentication_required" if "required" in detail else "authentication_failed"
    return _error_response(401, code, detail)


async def authorization_exception_handler(
    _request: Request, exc: AuthorizationError
) -> JSONResponse:
    return _error_response(403, "forbidden", str(exc))


async def permission_exception_handler(_request: Request, _exc: PermissionError) -> JSONResponse:
    return _error_response(403, "user_disabled", "user is disabled")


async def validation_exception_handler(_request: Request, exc: ValidationError) -> JSONResponse:
    detail = str(exc)
    if "size limit" in detail:
        return _error_response(413, "file_too_large", detail)
    return _error_response(422, "invalid_file", detail)


async def not_found_exception_handler(_request: Request, _exc: NotFoundError) -> JSONResponse:
    return _error_response(404, "not_found", "document was not found")


async def conflict_exception_handler(_request: Request, exc: RepositoryConflict) -> JSONResponse:
    return _error_response(409, "conflict", str(exc))


async def storage_exception_handler(_request: Request, exc: StorageError) -> JSONResponse:
    return _error_response(503, "storage_unavailable", str(exc))


async def dependency_exception_handler(_request: Request, exc: DependencyError) -> JSONResponse:
    return _error_response(503, "dependency_unavailable", str(exc))


async def transition_exception_handler(
    _request: Request, exc: InvalidStateTransition
) -> JSONResponse:
    return _error_response(409, "invalid_state_transition", str(exc))


async def ownership_exception_handler(_request: Request, exc: OwnershipError) -> JSONResponse:
    return _error_response(403, "forbidden", str(exc))


async def domain_exception_handler(_request: Request, exc: DomainError) -> JSONResponse:
    return _error_response(422, "invalid_request", str(exc))


async def unexpected_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled request failure",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    metrics.increment("api_unexpected_failures")
    return _error_response(500, "internal_error", "internal server error")


def register_exception_handlers(application: FastAPI) -> None:
    """Register shared public error responses in subclass-first order."""
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    application.add_exception_handler(AuthenticationError, authentication_exception_handler)
    application.add_exception_handler(InvalidStateTransition, transition_exception_handler)
    application.add_exception_handler(OwnershipError, ownership_exception_handler)
    application.add_exception_handler(AuthorizationError, authorization_exception_handler)
    application.add_exception_handler(NotFoundError, not_found_exception_handler)
    application.add_exception_handler(ValidationError, validation_exception_handler)
    application.add_exception_handler(RepositoryConflict, conflict_exception_handler)
    application.add_exception_handler(StorageError, storage_exception_handler)
    application.add_exception_handler(DependencyError, dependency_exception_handler)
    application.add_exception_handler(PermissionError, permission_exception_handler)
    application.add_exception_handler(DomainError, domain_exception_handler)
    application.add_exception_handler(Exception, unexpected_exception_handler)


__all__ = ["register_exception_handlers"]
