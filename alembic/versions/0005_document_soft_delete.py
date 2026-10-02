"""Add document soft-delete markers and actor audit fields."""

import sqlalchemy as sa

from alembic import op

revision = "0005_document_soft_delete"
down_revision = "0004_authentication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("deleted_by", sa.String(length=255), nullable=True))
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_documents_deleted_at", table_name="documents")
    op.drop_column("documents", "deleted_by")
    op.drop_column("documents", "deleted_at")
