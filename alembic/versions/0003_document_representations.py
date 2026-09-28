"""Persist versioned derived document representations."""

import sqlalchemy as sa

from alembic import op

revision = "0003_document_representations"
down_revision = "0002_outbox_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_representations",
        sa.Column("representation_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("processor", sa.String(length=255), nullable=False),
        sa.Column("processor_version", sa.String(length=255), nullable=False),
        sa.Column("logic_version", sa.String(length=255), nullable=False),
        sa.Column("storage_reference", sa.String(length=2048), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.artifact_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("representation_id"),
    )
    op.create_index(
        "ix_document_representations_document_id", "document_representations", ["document_id"]
    )
    op.create_index(
        "ix_document_representations_artifact_id", "document_representations", ["artifact_id"]
    )
    op.create_index("ix_document_representations_status", "document_representations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_document_representations_status", table_name="document_representations")
    op.drop_index("ix_document_representations_artifact_id", table_name="document_representations")
    op.drop_index("ix_document_representations_document_id", table_name="document_representations")
    op.drop_table("document_representations")
