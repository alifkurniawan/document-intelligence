import asyncio

from app.config import Settings
from app.infrastructure.database.models import ArtifactModel, DocumentModel, ProcessingJobModel
from app.infrastructure.database.session import Base, create_engine


def test_database_engine_is_async_and_does_not_connect_on_creation() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:password@example.test/app",
    )

    engine = create_engine(settings)

    try:
        assert engine.sync_engine.url.drivername == "postgresql+psycopg"
    finally:
        # Disposal does not require a live database connection.
        asyncio.run(engine.dispose())


def test_metadata_contains_confirmed_tables_and_original_index() -> None:
    assert {"documents", "artifacts", "processing_jobs"} <= set(Base.metadata.tables)
    assert ArtifactModel.__table__.name == "artifacts"
    assert DocumentModel.__table__.name == "documents"
    assert ProcessingJobModel.__table__.name == "processing_jobs"
    assert any(
        index.name == "uq_one_original_artifact_per_document"
        for index in ArtifactModel.__table__.indexes
    )


def test_models_have_owner_and_lookup_indexes() -> None:
    document_indexes = {index.name for index in DocumentModel.__table__.indexes}
    job_indexes = {index.name for index in ProcessingJobModel.__table__.indexes}

    assert "ix_documents_owner_id" in document_indexes
    assert "ix_processing_jobs_document_id" in job_indexes
    assert "ix_processing_jobs_status" in job_indexes
