"""Add the transactional outbox for processing hand-off."""

import sqlalchemy as sa

from alembic import op

revision = "0002_outbox_messages"
down_revision = "0001_initial_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_messages",
        sa.Column("outbox_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("original_artifact_id", sa.Uuid(), nullable=False),
        sa.Column("routing_key", sa.String(length=255), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["processing_jobs.job_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("outbox_id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_outbox_messages_pending", "outbox_messages", ["published_at", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_outbox_messages_pending", table_name="outbox_messages")
    op.drop_table("outbox_messages")
