"""Typed, environment-driven application configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

EnvironmentName = Literal["development", "test", "production"]


def _parse_list(value: Any) -> Any:
    """Accept comma-separated environment values as well as native lists."""

    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    """Runtime configuration loaded from unprefixed environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: EnvironmentName = "development"
    log_level: str = "INFO"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)

    max_upload_size_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    allowed_extensions: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx"]
    )
    allowed_mime_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "application/pdf",
            "image/jpeg",
            "image/png",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]
    )

    database_url: SecretStr | None = None

    rabbitmq_url: SecretStr | None = None
    rabbitmq_exchange: str = "document-ingestion"
    rabbitmq_queue: str = "document-processing"
    rabbitmq_routing_key: str = "document.process"
    rabbitmq_retry_count: int = Field(default=3, ge=0, le=3)
    rabbitmq_retry_base_delay_seconds: float = Field(default=1.0, gt=0)
    rabbitmq_retry_max_delay_seconds: float = Field(default=60.0, gt=0)
    rabbitmq_retry_jitter: bool = False
    rabbitmq_dlq_exchange: str = "document-ingestion-dlx"
    rabbitmq_dlq_queue: str = "document-processing-dlq"

    firebase_project_id: str | None = None
    firebase_credentials_path: str | None = None
    firebase_storage_bucket: str | None = None

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        allowed = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return normalized

    @field_validator("allowed_extensions", "allowed_mime_types", mode="before")
    @classmethod
    def parse_allowlist(cls, value: Any) -> Any:
        return _parse_list(value)

    @field_validator("allowed_extensions")
    @classmethod
    def normalize_extensions(cls, values: list[str]) -> list[str]:
        normalized = []
        for value in values:
            extension = value.lower()
            if not extension.startswith(".") or extension == ".":
                raise ValueError("allowed_extensions must contain values such as '.pdf'")
            normalized.append(extension)
        if len(set(normalized)) != len(normalized):
            raise ValueError("allowed_extensions must not contain duplicates")
        if not normalized:
            raise ValueError("allowed_extensions must not be empty")
        return normalized

    @field_validator("allowed_mime_types")
    @classmethod
    def normalize_mime_types(cls, values: list[str]) -> list[str]:
        normalized = [value.lower() for value in values]
        if len(set(normalized)) != len(normalized):
            raise ValueError("allowed_mime_types must not contain duplicates")
        if not normalized:
            raise ValueError("allowed_mime_types must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_configuration(self) -> Settings:
        if self.rabbitmq_retry_base_delay_seconds > self.rabbitmq_retry_max_delay_seconds:
            raise ValueError("rabbitmq_retry_base_delay_seconds cannot exceed max delay")
        if self.rabbitmq_retry_count != 3:
            raise ValueError("rabbitmq_retry_count must be exactly 3")

        for field_name in ("database_url", "rabbitmq_url"):
            value = getattr(self, field_name)
            if value is not None:
                parsed = urlparse(value.get_secret_value())
                if not parsed.scheme or not parsed.netloc:
                    raise ValueError(f"{field_name} must be a valid connection URL")

        if self.environment == "production":
            required = {
                "database_url": self.database_url,
                "rabbitmq_url": self.rabbitmq_url,
                "firebase_project_id": self.firebase_project_id,
                "firebase_credentials_path": self.firebase_credentials_path,
                "firebase_storage_bucket": self.firebase_storage_bucket,
            }
            missing = [name.upper() for name, value in required.items() if not value]
            if missing:
                raise ValueError(
                    "production configuration is missing required settings: " + ", ".join(missing)
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process settings singleton."""

    return Settings()


__all__ = ["EnvironmentName", "Settings", "get_settings"]
