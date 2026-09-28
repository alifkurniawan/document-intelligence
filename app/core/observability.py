"""Small provider-neutral observability primitives.

Correlation identifiers are deliberately kept in process context only; they are
safe to copy into logs and asynchronous messages, but never contain credentials
or document contents.
"""

from __future__ import annotations

import logging
import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import Lock
from uuid import uuid4

_CORRELATION_ID: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def new_correlation_id(candidate: str | None = None) -> str:
    """Return a validated caller id or generate an opaque request id."""

    if candidate and _SAFE_ID.fullmatch(candidate):
        return candidate
    return str(uuid4())


def set_correlation_id(value: str) -> None:
    _CORRELATION_ID.set(value)


def correlation_id() -> str:
    return _CORRELATION_ID.get() or new_correlation_id()


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id()
        return True


@dataclass
class Metrics:
    """In-process counters suitable for health/metrics adapters later."""

    _values: dict[str, int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._values[name] = self._values.get(name, 0) + amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._values)


metrics = Metrics()


__all__ = [
    "CorrelationFilter",
    "Metrics",
    "correlation_id",
    "metrics",
    "new_correlation_id",
    "set_correlation_id",
]
