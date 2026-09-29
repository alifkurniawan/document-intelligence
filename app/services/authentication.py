"""Application authentication orchestration and token lifecycle."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import FirebaseAuthVerifier
from app.core.config import Settings
from app.core.ingestion_errors import AuthenticationError
from app.repositories.auth import SqlAlchemyAuthRepository


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


class ApplicationTokenService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        key = (
            settings.jwt_signing_key.get_secret_value()
            if settings.jwt_signing_key
            else secrets.token_urlsafe(32)
        )
        self._key = key

    def issue_access_token(self, *, user_id: UUID, firebase_uid: str) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": str(user_id),
                "firebase_uid": firebase_uid,
                "type": "access",
                "iss": self.settings.auth_issuer,
                "aud": self.settings.auth_audience,
                "iat": now,
                "exp": now + timedelta(seconds=self.settings.access_token_expire_seconds),
            },
            self._key,
            algorithm="HS256",
        )

    def verify_access_token(self, token: str) -> tuple[UUID, str]:
        try:
            claims = jwt.decode(
                token,
                self._key,
                algorithms=["HS256"],
                issuer=self.settings.auth_issuer,
                audience=self.settings.auth_audience,
            )
            if claims.get("type") != "access" or not claims.get("firebase_uid"):
                raise ValueError
            return UUID(str(claims["sub"])), str(claims["firebase_uid"])
        except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
            raise AuthenticationError("invalid access token") from exc

    @staticmethod
    def new_refresh_token() -> str:
        return secrets.token_urlsafe(48)

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthenticationService:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], settings: Settings
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.firebase_verifier = FirebaseAuthVerifier(settings)
        self.tokens = ApplicationTokenService(settings)

    async def exchange_firebase_token(self, id_token: str) -> TokenPair:
        identity = await self.firebase_verifier.verify_identity(id_token)
        async with self.session_factory() as session:
            repository = SqlAlchemyAuthRepository(session)
            user = await repository.upsert_user(
                firebase_uid=identity.uid,
                email=identity.email,
                email_verified=identity.email_verified,
            )
            if not user.active:
                raise PermissionError("user is disabled")
            refresh_token = self.tokens.new_refresh_token()
            await repository.add_refresh_token(
                user_id=user.user_id,
                token_hash=self.tokens.hash_refresh_token(refresh_token),
                expires_at=datetime.now(UTC)
                + timedelta(seconds=self.settings.refresh_token_expire_seconds),
            )
            await session.commit()
            return TokenPair(
                access_token=self.tokens.issue_access_token(
                    user_id=user.user_id, firebase_uid=user.firebase_uid
                ),
                refresh_token=refresh_token,
            )

    async def refresh(self, refresh_token: str) -> TokenPair:
        if not refresh_token:
            raise AuthenticationError("invalid refresh token")
        async with self.session_factory() as session:
            repository = SqlAlchemyAuthRepository(session)
            stored = await repository.refresh_token_by_hash(
                self.tokens.hash_refresh_token(refresh_token)
            )
            now = datetime.now(UTC)
            if stored is None or stored.revoked_at is not None or stored.expires_at <= now:
                raise AuthenticationError("invalid refresh token")
            user = await repository.user_by_id(stored.user_id)
            if user is None or not user.active:
                raise AuthenticationError("invalid refresh token")
            await repository.revoke_refresh_token(stored)
            replacement = self.tokens.new_refresh_token()
            await repository.add_refresh_token(
                user_id=user.user_id,
                token_hash=self.tokens.hash_refresh_token(replacement),
                expires_at=now + timedelta(seconds=self.settings.refresh_token_expire_seconds),
            )
            await session.commit()
            return TokenPair(
                access_token=self.tokens.issue_access_token(
                    user_id=user.user_id, firebase_uid=user.firebase_uid
                ),
                refresh_token=replacement,
            )

    async def logout(self, refresh_token: str) -> None:
        async with self.session_factory() as session:
            repository = SqlAlchemyAuthRepository(session)
            stored = await repository.refresh_token_by_hash(
                self.tokens.hash_refresh_token(refresh_token)
            )
            if stored is not None and stored.revoked_at is None:
                await repository.revoke_refresh_token(stored)
                await session.commit()

    async def resolve_active_user(self, user_id: UUID):
        async with self.session_factory() as session:
            user = await SqlAlchemyAuthRepository(session).user_by_id(user_id)
            if user is None:
                raise AuthenticationError("invalid access token")
            if not user.active:
                raise PermissionError("user is disabled")
            return user
