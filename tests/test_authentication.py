import asyncio
from datetime import timedelta
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.api.auth import FirebaseAuthVerifier
from app.core.config import Settings
from app.core.ingestion_errors import AuthenticationError
from app.services.authentication import ApplicationTokenService, TokenPair


def test_application_access_token_round_trip_and_rejections() -> None:
    test_key = "test-key-0123456789-0123456789-0123"
    settings = Settings(_env_file=None, jwt_signing_key=test_key, access_token_expire_seconds=900)
    service = ApplicationTokenService(settings)
    user_id = uuid4()
    token = service.issue_access_token(user_id=user_id, firebase_uid="firebase-1")

    assert service.verify_access_token(token) == (user_id, "firebase-1")
    for invalid in ("not-a-jwt", token + "x"):
        try:
            service.verify_access_token(invalid)
        except AuthenticationError:
            pass
        else:
            raise AssertionError("invalid access token was accepted")

    expired = jwt.encode(
        {
            "sub": str(user_id),
            "firebase_uid": "firebase-1",
            "type": "access",
            "iss": settings.auth_issuer,
            "aud": settings.auth_audience,
            "exp": __import__("datetime").datetime.now(__import__("datetime").UTC)
            - timedelta(seconds=1),
        },
        test_key,
        algorithm="HS256",
    )
    try:
        service.verify_access_token(expired)
    except AuthenticationError:
        pass
    else:
        raise AssertionError("expired access token was accepted")


def test_firebase_verifier_uses_admin_verification(monkeypatch) -> None:
    monkeypatch.setattr("app.api.auth.initialize_firebase", lambda settings: None)
    monkeypatch.setattr(
        "app.api.auth.auth.verify_id_token",
        lambda token: {"uid": "firebase-1", "email": "user@example.test", "email_verified": True},
    )
    identity = asyncio.run(
        FirebaseAuthVerifier(Settings(_env_file=None)).verify_identity("firebase-token")
    )
    assert identity.uid == "firebase-1"
    assert identity.email_verified is True


class FakeAuthService:
    async def exchange_firebase_token(self, token: str) -> TokenPair:
        assert token == "firebase-token"
        return TokenPair("access", "refresh")

    async def refresh(self, token: str) -> TokenPair:
        return TokenPair("new-access", "new-refresh")

    async def logout(self, token: str) -> None:
        return None


def test_auth_endpoints_handle_missing_token_and_refresh() -> None:
    app = create_app(Settings(_env_file=None, access_token_expire_seconds=900))
    app.state.authentication_service = FakeAuthService()
    with TestClient(app) as client:
        assert client.post("/auth/token", json={}).status_code == 401
        response = client.post("/auth/token", json={"id_token": "firebase-token"})
        assert response.status_code == 200
        assert response.json()["token_type"] == "Bearer"
        assert client.post("/auth/refresh", json={"refresh_token": "refresh"}).status_code == 200
