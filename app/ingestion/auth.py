"""Authentication port and Firebase token adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.ingestion.errors import AuthenticationError


@dataclass(frozen=True, slots=True)
class AuthenticatedOwner:
    owner_id: str


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> AuthenticatedOwner: ...


class FirebaseAuthVerifier:
    """Verify Firebase email-auth ID tokens without exposing the SDK to routes."""

    async def verify(self, token: str) -> AuthenticatedOwner:
        if not token:
            raise AuthenticationError("authentication token is required")
        try:
            import asyncio

            from firebase_admin import auth

            claims = await asyncio.to_thread(auth.verify_id_token, token)
        except Exception as exc:
            raise AuthenticationError("invalid authentication token") from exc
        subject = claims.get("uid")
        if not isinstance(subject, str) or not subject:
            raise AuthenticationError("authentication token has no owner identity")
        return AuthenticatedOwner(owner_id=subject)


class StaticTokenVerifier:
    """Small deterministic verifier useful for local development and tests."""

    def __init__(self, tokens: dict[str, str]) -> None:
        self.tokens = tokens

    async def verify(self, token: str) -> AuthenticatedOwner:
        owner_id = self.tokens.get(token)
        if owner_id is None:
            raise AuthenticationError("invalid authentication token")
        return AuthenticatedOwner(owner_id=owner_id)
