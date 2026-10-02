"""Shared API response envelopes and pagination metadata."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    data: T
    message: str


class PaginatedData(BaseModel, Generic[T]):
    data: list[T]
    current_page: int
    total_data: int
    total_page: int


class ErrorData(BaseModel):
    code: str
    correlation_id: str


class ErrorResponse(ApiResponse[ErrorData]):
    pass


__all__ = ["ApiResponse", "ErrorData", "ErrorResponse", "PaginatedData"]
