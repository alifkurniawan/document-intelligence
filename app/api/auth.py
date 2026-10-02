"""Authentication port and Firebase token adapter."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from app.core.config import Settings
from app.core.firebase import initialize_firebase
from app.core.ingestion_errors import AuthenticationError


@dataclass(frozen=True, slots=True)
class AuthenticatedOwner:
    owner_id: str
    firebase_uid: str | None = None


@dataclass(frozen=True, slots=True)
class FirebaseIdentity:
    uid: str
    email: str | None
    email_verified: bool


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> AuthenticatedOwner: ...


class FirebaseAuthVerifier:
    """Verify Firebase email-auth ID tokens without exposing the SDK to routes."""

    def __init__(self, settings: Settings) -> None:
        initialize_firebase(settings)

    async def verify(self, token: str) -> AuthenticatedOwner:
        identity = await self.verify_identity(token)
        return AuthenticatedOwner(owner_id=identity.uid)

    async def verify_identity(self, token: str) -> FirebaseIdentity:
        if not token:
            raise AuthenticationError("authentication token is required")
        try:
            claims = await asyncio.to_thread(auth.verify_id_token, token)
        except Exception as exc:
            raise AuthenticationError("invalid authentication token") from exc
        subject = claims.get("uid")
        if not isinstance(subject, str) or not subject:
            raise AuthenticationError("authentication token has no owner identity")
        return FirebaseIdentity(
            uid=subject,
            email=claims.get("email") if isinstance(claims.get("email"), str) else None,
            email_verified=claims.get("email_verified") is True,
        )


class StaticTokenVerifier:
    """Small deterministic verifier useful for local development and tests."""

    def __init__(self, tokens: dict[str, str]) -> None:
        self.tokens = tokens

    async def verify(self, token: str) -> AuthenticatedOwner:
        owner_id = self.tokens.get(token)
        if owner_id is None:
            raise AuthenticationError("invalid authentication token")
        return AuthenticatedOwner(owner_id=owner_id)


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))
    ],
) -> AuthenticatedOwner:
    """Reusable DI dependency for application Bearer access tokens."""
    if credentials is None:
        raise AuthenticationError("Bearer token is required")
    token = credentials.credentials.strip()
    verifier: TokenVerifier = request.app.state.token_verifier
    current = await verifier.verify(token)
    auth_service = getattr(request.app.state, "authentication_service", None)
    if auth_service is not None:
        try:
            user_id = UUID(current.owner_id)
        except ValueError as exc:
            raise AuthenticationError("invalid access token") from exc
        await auth_service.resolve_active_user(user_id)
    return current


__all__ = [
    "AuthenticatedOwner",
    "FirebaseIdentity",
    "FirebaseAuthVerifier",
    "StaticTokenVerifier",
    "TokenVerifier",
    "get_current_user",
]
