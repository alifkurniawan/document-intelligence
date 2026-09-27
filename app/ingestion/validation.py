"""Bounded, technical validation for supported document formats."""

from __future__ import annotations

import hashlib
import io
import mimetypes
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import PurePath
from typing import BinaryIO

from PIL import Image, UnidentifiedImageError

from app.config import Settings
from app.ingestion.errors import ValidationError

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(slots=True)
class ValidatedFile:
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    stream: BinaryIO

    def close(self) -> None:
        self.stream.close()


def _safe_filename(filename: str | None) -> str:
    if (
        not filename
        or "\x00" in filename
        or "\\" in filename
        or filename != PurePath(filename).name
    ):
        raise ValidationError("filename is unsafe")
    normalized = filename.strip()
    if not normalized or normalized in {".", ".."}:
        raise ValidationError("filename is unsafe")
    return normalized


class FileValidator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate(
        self, *, filename: str | None, client_mime: str | None, source: bytes | bytearray | BinaryIO
    ) -> ValidatedFile:
        safe_name = _safe_filename(filename)
        stream = tempfile.SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
        if isinstance(source, (bytes, bytearray)):
            reader = io.BytesIO(source)
        else:
            reader = source
        reader.seek(0)
        digest = hashlib.sha256()
        size = 0
        while chunk := reader.read(1024 * 1024):
            size += len(chunk)
            if size > self.settings.max_upload_size_bytes:
                stream.close()
                raise ValidationError("file exceeds the configured size limit")
            digest.update(chunk)
            stream.write(chunk)
        if size == 0:
            stream.close()
            raise ValidationError("file is empty")
        stream.seek(0)
        mime = self._detect_mime(stream, safe_name)
        extension = self._extension(safe_name)
        if extension not in self.settings.allowed_extensions:
            stream.close()
            raise ValidationError("file extension is not supported")
        if mime not in self.settings.allowed_mime_types:
            stream.close()
            raise ValidationError("file content type is not supported")
        if client_mime and client_mime.lower().split(";", 1)[0].strip() != mime:
            stream.close()
            raise ValidationError("declared MIME type does not match file content")
        if not self._extension_matches(extension, mime):
            stream.close()
            raise ValidationError("file extension does not match file content")
        self._check_integrity(stream, mime)
        stream.seek(0)
        return ValidatedFile(safe_name, mime, size, digest.hexdigest(), stream)

    @staticmethod
    def _extension(filename: str) -> str:
        return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    @staticmethod
    def _detect_mime(stream: BinaryIO, filename: str) -> str:
        stream.seek(0)
        prefix = stream.read(16)
        stream.seek(0)
        if prefix.startswith(b"%PDF-"):
            return "application/pdf"
        if prefix.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if prefix.startswith(b"PK\x03\x04"):
            try:
                with zipfile.ZipFile(stream) as archive:
                    names = set(archive.namelist())
                    if "word/document.xml" in names:
                        return DOCX_MIME
                    if "xl/workbook.xml" in names:
                        return XLSX_MIME
            except zipfile.BadZipFile, OSError:
                pass
        try:
            with Image.open(stream) as image:
                detected = Image.MIME.get(image.format)
                if detected:
                    return detected
        except UnidentifiedImageError, OSError:
            pass
        guessed, _ = mimetypes.guess_type(filename)
        raise ValidationError(
            f"file content is unreadable or unsupported (detected {guessed or 'unknown'})"
        )

    @staticmethod
    def _extension_matches(extension: str, mime: str) -> bool:
        expected = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".docx": DOCX_MIME,
            ".xlsx": XLSX_MIME,
        }
        return (
            expected.get(extension) == mime or mimetypes.guess_type("file" + extension)[0] == mime
        )

    @staticmethod
    def _check_integrity(stream: BinaryIO, mime: str) -> None:
        stream.seek(0)
        try:
            if mime.startswith("image/"):
                with Image.open(stream) as image:
                    image.verify()
            elif mime.endswith("document") or mime.endswith("sheet"):
                with zipfile.ZipFile(stream) as archive:
                    if archive.testzip() is not None:
                        raise ValidationError("Office document is corrupt")
            elif mime == "application/pdf":
                data = stream.read()
                if b"%%EOF" not in data[-1024:]:
                    raise ValidationError("PDF is corrupt or incomplete")
        except (UnidentifiedImageError, OSError, zipfile.BadZipFile) as exc:
            raise ValidationError("file is corrupt or unreadable") from exc
