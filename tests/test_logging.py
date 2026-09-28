import logging

from app.api.app import configure_logging


def test_logging_uses_safe_default(monkeypatch) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    configure_logging()

    assert logging.getLogger().level == logging.INFO


def test_logging_accepts_environment_level(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")
    configure_logging()

    assert logging.getLogger().level == logging.DEBUG
