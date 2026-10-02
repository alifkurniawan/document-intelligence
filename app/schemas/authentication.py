"""HTTP request and response contracts for authentication."""

from pydantic import BaseModel


class FirebaseTokenRequest(BaseModel):
    id_token: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None


__all__ = ["AccessTokenResponse", "FirebaseTokenRequest", "RefreshTokenRequest"]
