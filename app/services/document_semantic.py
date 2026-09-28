"""Generic document-level semantic observations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from app.models.understanding import DocumentRepresentation


class SemanticType(StrEnum):
    DATE = "date"
    MONEY = "monetary_amount"
    DOCUMENT_IDENTIFIER = "document_identifier"


@dataclass(frozen=True, slots=True)
class SemanticObservation:
    type: SemanticType
    value: str
    source_text: str


class GenericSemanticExtractor:
    _patterns = (
        (SemanticType.DATE, re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b")),
        (SemanticType.MONEY, re.compile(r"\b(?:USD|EUR|IDR|Rp)\s?[\d.,]+\b", re.I)),
        (
            SemanticType.DOCUMENT_IDENTIFIER,
            re.compile(r"\b(?:No\.?|ID)\s?[A-Z0-9][A-Z0-9./-]{2,}\b", re.I),
        ),
    )

    def extract(self, representation: DocumentRepresentation) -> tuple[SemanticObservation, ...]:
        return tuple(
            SemanticObservation(kind, match.group(0), match.group(0))
            for kind, pattern in self._patterns
            for match in pattern.finditer(representation.text)
        )


__all__ = ["GenericSemanticExtractor", "SemanticObservation", "SemanticType"]
