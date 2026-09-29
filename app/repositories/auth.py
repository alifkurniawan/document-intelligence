"""Persistence boundary for application users and refresh-token sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import RefreshTokenModel, UserModel


class SqlAlchemyAuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def user_by_firebase_uid(self, firebase_uid: str) -> UserModel | None:
        return await self.session.scalar(
            select(UserModel).where(UserModel.firebase_uid == firebase_uid)
        )

    async def user_by_id(self, user_id: UUID) -> UserModel | None:
        return await self.session.get(UserModel, user_id)

    async def upsert_user(
        self, *, firebase_uid: str, email: str | None, email_verified: bool
    ) -> UserModel:
        user = await self.user_by_firebase_uid(firebase_uid)
        now = datetime.now(UTC)
        if user is None:
            user = UserModel(
                user_id=uuid4(),
                firebase_uid=firebase_uid,
                email=email,
                email_verified=email_verified,
                active=True,
                created_at=now,
                updated_at=now,
            )
            self.session.add(user)
        else:
            user.email = email
            user.email_verified = email_verified
            user.updated_at = now
        await self.session.flush()
        return user

    async def add_refresh_token(
        self, *, user_id: UUID, token_hash: str, expires_at: datetime
    ) -> RefreshTokenModel:
        token = RefreshTokenModel(
            refresh_token_id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
            revoked_at=None,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def refresh_token_by_hash(self, token_hash: str) -> RefreshTokenModel | None:
        return await self.session.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )

    async def revoke_refresh_token(self, token: RefreshTokenModel) -> None:
        token.revoked_at = datetime.now(UTC)
        await self.session.flush()
