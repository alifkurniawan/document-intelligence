"""Application token endpoints; Firebase remains the identity provider."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.ingestion_errors import AuthenticationError, DependencyError
from app.schemas.authentication import (
    AccessTokenResponse,
    FirebaseTokenRequest,
    RefreshTokenRequest,
)
from app.schemas.responses import ApiResponse
from app.services.authentication import AuthenticationService, TokenPair


def _pair_response(
    pair: TokenPair, expires_in: int, *, message: str
) -> ApiResponse[AccessTokenResponse]:
    return ApiResponse(
        data=AccessTokenResponse(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            expires_in=expires_in,
        ),
        message=message,
    )


def create_auth_router(*, get_auth_service, get_settings) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["authentication"])

    def service_or_error(service: AuthenticationService | None) -> AuthenticationService:
        if service is None:
            raise DependencyError("authentication is not configured")
        return service

    @router.post(
        "/token",
        response_model=ApiResponse[AccessTokenResponse],
        responses={401: {"description": "Invalid Firebase ID token"}},
    )
    async def exchange_token(
        service=Depends(get_auth_service),
        payload: FirebaseTokenRequest | None = None,
    ) -> ApiResponse[AccessTokenResponse]:
        if payload is None or not payload.id_token:
            raise AuthenticationError("id token is required")
        pair = await service_or_error(service).exchange_firebase_token(payload.id_token)
        return _pair_response(
            pair,
            get_settings().access_token_expire_seconds,
            message="Authentication successful.",
        )

    @router.post(
        "/refresh",
        response_model=ApiResponse[AccessTokenResponse],
        responses={401: {"description": "Invalid or revoked refresh token"}},
    )
    async def refresh_token(
        service=Depends(get_auth_service),
        payload: RefreshTokenRequest | None = None,
    ) -> ApiResponse[AccessTokenResponse]:
        if payload is None or not payload.refresh_token:
            raise AuthenticationError("invalid refresh token")
        pair = await service_or_error(service).refresh(payload.refresh_token)
        return _pair_response(
            pair,
            get_settings().access_token_expire_seconds,
            message="Token refreshed.",
        )

    @router.post(
        "/logout",
        response_model=ApiResponse[None],
        responses={401: {"description": "Invalid session"}},
    )
    async def logout(
        service=Depends(get_auth_service),
        payload: RefreshTokenRequest | None = None,
    ) -> ApiResponse[None]:
        if payload is not None and payload.refresh_token:
            await service_or_error(service).logout(payload.refresh_token)
        return ApiResponse(data=None, message="Logout completed.")

    return router
