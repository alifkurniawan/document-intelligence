import logging

import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.main import configure_logging


def test_defaults_are_safe_for_local_development() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.max_upload_size_bytes == 25 * 1024 * 1024
    assert settings.rabbitmq_retry_count == 3
    assert settings.allowed_extensions == [".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx"]


def test_environment_overrides_are_typed_and_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_BYTES", "1024")
    monkeypatch.setenv("ALLOWED_EXTENSIONS", ".PDF, .PNG")
    monkeypatch.setenv("ALLOWED_MIME_TYPES", "application/pdf, image/png")
    monkeypatch.setenv("RABBITMQ_RETRY_JITTER", "true")

    settings = Settings(_env_file=None)

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.api_port == 9000
    assert settings.max_upload_size_bytes == 1024
    assert settings.allowed_extensions == [".pdf", ".png"]
    assert settings.allowed_mime_types == ["application/pdf", "image/png"]
    assert settings.rabbitmq_retry_jitter is True


def test_production_requires_external_service_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None)


def test_invalid_configuration_is_rejected() -> None:
    with pytest.raises(ValidationError, match="api_port"):
        Settings(_env_file=None, api_port=70000)

    with pytest.raises(ValidationError, match="rabbitmq_retry_count"):
        Settings(_env_file=None, rabbitmq_retry_count=2)


def test_connection_values_are_hidden_from_repr() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:password@example.test/app",
    )

    assert "password" not in repr(settings)


def test_settings_are_cached_and_logging_uses_the_configuration_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("LOG_LEVEL", "debug")
    configure_logging(get_settings())

    assert logging.getLogger().level == logging.DEBUG
