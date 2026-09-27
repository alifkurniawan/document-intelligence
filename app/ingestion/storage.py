"""Replaceable artifact storage ports and safe original adapters."""

from __future__ import annotations

import asyncio
import hashlib
import io
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import UUID

from app.ingestion.errors import StorageError


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    storage_reference: str
    size_bytes: int
    sha256: str
    stored_at: datetime


class ArtifactStorage(Protocol):
    async def store(
        self,
        *,
        document_id: UUID,
        filename: str,
        source: BinaryIO,
        expected_size: int,
        expected_sha256: str,
    ) -> StoredArtifact: ...
    async def read(self, storage_reference: str) -> bytes: ...
    async def delete(self, storage_reference: str) -> None: ...


def _copy_and_hash(source: BinaryIO) -> tuple[bytes, int, str]:
    source.seek(0)
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    size = 0
    while chunk := source.read(1024 * 1024):
        digest.update(chunk)
        chunks.append(chunk)
        size += len(chunk)
    return b"".join(chunks), size, digest.hexdigest()


class InMemoryArtifactStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def store(self, *, document_id, filename, source, expected_size, expected_sha256):
        data, size, digest = await asyncio.to_thread(_copy_and_hash, source)
        if size != expected_size or digest != expected_sha256:
            raise StorageError("stored artifact verification failed")
        reference = f"documents/{document_id}/original/{filename}"
        if reference in self.objects:
            raise StorageError("original artifact already exists")
        self.objects[reference] = data
        return StoredArtifact(reference, size, digest, datetime.now(UTC))

    async def read(self, storage_reference: str) -> bytes:
        try:
            return self.objects[storage_reference]
        except KeyError as exc:
            raise StorageError("stored artifact was not found") from exc

    async def delete(self, storage_reference: str) -> None:
        self.objects.pop(storage_reference, None)


class FilesystemArtifactStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, reference: str) -> Path:
        path = (self.root / reference).resolve()
        if self.root.resolve() not in path.parents:
            raise StorageError("invalid storage reference")
        return path

    async def store(self, *, document_id, filename, source, expected_size, expected_sha256):
        data, size, digest = await asyncio.to_thread(_copy_and_hash, source)
        if size != expected_size or digest != expected_sha256:
            raise StorageError("stored artifact verification failed")
        reference = f"documents/{document_id}/original/{filename}"
        path = self._path(reference)

        def write_exclusive() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(data)

        try:
            await asyncio.to_thread(write_exclusive)
        except FileExistsError as exc:
            raise StorageError("original artifact already exists") from exc
        return StoredArtifact(reference, size, digest, datetime.now(UTC))

    async def read(self, storage_reference: str) -> bytes:
        try:
            return await asyncio.to_thread(self._path(storage_reference).read_bytes)
        except FileNotFoundError as exc:
            raise StorageError("stored artifact was not found") from exc

    async def delete(self, storage_reference: str) -> None:
        path = self._path(storage_reference)
        try:
            await asyncio.to_thread(path.unlink)
        except FileNotFoundError:
            return


class FirebaseArtifactStorage:
    """Firebase Storage adapter; SDK calls are isolated behind this port."""

    def __init__(self, bucket_name: str) -> None:
        self.bucket_name = bucket_name

    async def store(self, *, document_id, filename, source, expected_size, expected_sha256):
        data, size, digest = await asyncio.to_thread(_copy_and_hash, source)
        if size != expected_size or digest != expected_sha256:
            raise StorageError("stored artifact verification failed")
        reference = f"documents/{document_id}/original/{filename}"

        def upload() -> None:
            from firebase_admin import storage

            blob = storage.bucket(self.bucket_name).blob(reference)
            if blob.exists():
                raise StorageError("original artifact already exists")
            blob.upload_from_file(io.BytesIO(data), rewind=True)

        try:
            await asyncio.to_thread(upload)
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError("Firebase Storage upload failed") from exc
        return StoredArtifact(reference, size, digest, datetime.now(UTC))

    async def read(self, storage_reference: str) -> bytes:
        try:
            from firebase_admin import storage

            return await asyncio.to_thread(
                storage.bucket(self.bucket_name).blob(storage_reference).download_as_bytes
            )
        except Exception as exc:
            raise StorageError("Firebase Storage read failed") from exc

    async def delete(self, storage_reference: str) -> None:
        try:
            from firebase_admin import storage

            await asyncio.to_thread(storage.bucket(self.bucket_name).blob(storage_reference).delete)
        except Exception as exc:
            raise StorageError("Firebase Storage cleanup failed") from exc
