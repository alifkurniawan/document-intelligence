"""Application token endpoints; Firebase remains the identity provider."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.authentication import AuthenticationService, TokenPair


class FirebaseTokenRequest(BaseModel):
    id_token: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None


def _pair_response(pair: TokenPair, expires_in: int) -> AccessTokenResponse:
    return AccessTokenResponse(
        access_token=pair.access_token, refresh_token=pair.refresh_token, expires_in=expires_in
    )


def create_auth_router(*, get_auth_service, get_settings) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["authentication"])

    def service_or_error(service: AuthenticationService | None) -> AuthenticationService:
        if service is None:
            raise HTTPException(
                503,
                {"code": "dependency_unavailable", "detail": "authentication is not configured"},
            )
        return service

    @router.post(
        "/token",
        response_model=AccessTokenResponse,
        responses={401: {"description": "Invalid Firebase ID token"}},
    )
    async def exchange_token(
        service=Depends(get_auth_service),
        payload: FirebaseTokenRequest | None = None,
    ) -> AccessTokenResponse:
        try:
            if payload is None or not payload.id_token:
                raise HTTPException(
                    401, {"code": "authentication_required", "detail": "id token is required"}
                )
            pair = await service_or_error(service).exchange_firebase_token(payload.id_token)
        except HTTPException:
            raise
        except PermissionError as exc:
            raise HTTPException(
                403, {"code": "user_disabled", "detail": "user is disabled"}
            ) from exc
        except Exception as exc:
            from app.core.ingestion_errors import AuthenticationError

            if isinstance(exc, AuthenticationError):
                raise HTTPException(
                    401, {"code": "authentication_failed", "detail": "invalid Firebase ID token"}
                ) from exc
            raise
        return _pair_response(pair, get_settings().access_token_expire_seconds)

    @router.post(
        "/refresh",
        response_model=AccessTokenResponse,
        responses={401: {"description": "Invalid or revoked refresh token"}},
    )
    async def refresh_token(
        service=Depends(get_auth_service),
        payload: RefreshTokenRequest | None = None,
    ) -> AccessTokenResponse:
        from app.core.ingestion_errors import AuthenticationError

        try:
            if payload is None or not payload.refresh_token:
                raise AuthenticationError("invalid refresh token")
            pair = await service_or_error(service).refresh(payload.refresh_token)
        except AuthenticationError as exc:
            raise HTTPException(
                401, {"code": "authentication_failed", "detail": "invalid refresh token"}
            ) from exc
        return _pair_response(pair, get_settings().access_token_expire_seconds)

    @router.post("/logout", status_code=204, responses={401: {"description": "Invalid session"}})
    async def logout(
        service=Depends(get_auth_service),
        payload: RefreshTokenRequest | None = None,
    ) -> None:
        if payload is not None and payload.refresh_token:
            await service_or_error(service).logout(payload.refresh_token)

    return router
