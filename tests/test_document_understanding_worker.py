from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.models.entities import Artifact, Document, ProcessingJob
from app.models.understanding import BlockType, ContentBlock, PageRepresentation
from app.services.document_processors import ProcessorResult
from app.services.document_understanding import DocumentUnderstandingService
from app.workers.contracts import ProcessingMessage
from app.workers.document_understanding import DocumentUnderstandingWorker


class MemoryReadStorage:
    def __init__(self, data: bytes = b"document") -> None:
        self.data = data

    async def read(self, storage_reference: str) -> bytes:
        return self.data


class SuccessfulProcessor:
    name = "test-processor"
    version = "test-1"

    def process(self, data: bytes) -> ProcessorResult:
        block = ContentBlock(type=BlockType.TEXT, text=data.decode(), page_number=1)
        return ProcessorResult((PageRepresentation(1, blocks=(block,)),), (block,))


class RetryableProcessor:
    name = "retryable-processor"
    version = "test-1"

    def process(self, data: bytes) -> ProcessorResult:
        raise RuntimeError("temporary processor failure")


class PermanentProcessor:
    name = "permanent-processor"
    version = "test-1"

    def process(self, data: bytes) -> ProcessorResult:
        raise ValueError("malformed document")


@dataclass
class JobRepository:
    job: ProcessingJob
    updated: list[ProcessingJob] = field(default_factory=list)

    async def get(self, job_id):
        return self.job if job_id == self.job.job_id else None

    async def update(self, job):
        self.job = job
        self.updated.append(job)
        return job


@dataclass
class ArtifactRepository:
    artifact: Artifact

    async def get(self, artifact_id):
        return self.artifact if artifact_id == self.artifact.artifact_id else None


@dataclass
class RepresentationRepository:
    values: list = field(default_factory=list)

    async def add(self, representation):
        self.values.append(representation)
        return representation


class UnitOfWork:
    def __init__(self, job, artifact):
        self.jobs = JobRepository(job)
        self.artifacts = ArtifactRepository(artifact)
        self.representations = RepresentationRepository()
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self):
        self.committed = True


def setup(processor):
    document = Document.create(owner_id="owner-1")
    artifact = Artifact.create_original(
        document_id=document.document_id,
        original_filename="document.pdf",
        mime_type="application/pdf",
        size_bytes=8,
        sha256="a" * 64,
        storage_reference="documents/document/original/document.pdf",
    )
    job = ProcessingJob.create(
        document_id=document.document_id, original_artifact_id=artifact.artifact_id
    )
    unit_of_work = UnitOfWork(job, artifact)
    service = DocumentUnderstandingService(
        storage=MemoryReadStorage(), processors={"application/pdf": processor}
    )
    worker = DocumentUnderstandingWorker(
        unit_of_work_factory=lambda: unit_of_work,
        understanding_service=service,
    )
    message = ProcessingMessage(document.document_id, job.job_id, artifact.artifact_id)
    return worker, unit_of_work, message


def test_worker_persists_representation_and_completes_job() -> None:
    worker, unit_of_work, message = setup(SuccessfulProcessor())

    decision = asyncio.run(worker.handle(message))

    assert decision.action == "ack"
    assert decision.job.status == "completed"
    assert len(unit_of_work.representations.values) == 1
    assert unit_of_work.committed is True


def test_worker_requeues_retryable_processing_failure() -> None:
    worker, unit_of_work, message = setup(RetryableProcessor())

    decision = asyncio.run(worker.handle(message))

    assert decision.action == "retry"
    assert decision.job.status == "queued"
    assert decision.job.retry_count == 1
    assert decision.error == "temporary processor failure"
    assert unit_of_work.representations.values == []


def test_worker_dead_letters_permanent_processing_failure() -> None:
    worker, unit_of_work, message = setup(PermanentProcessor())

    decision = asyncio.run(worker.handle(message))

    assert decision.action == "dead_letter"
    assert decision.job.status == "failed"
    assert decision.job.last_error == "malformed document"
    assert unit_of_work.committed is True
