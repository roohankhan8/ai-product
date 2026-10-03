"""Add durable document ingestion jobs."""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003_ingestion_jobs"
down_revision: Union[str, None] = "0002_document_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("attempts", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'running', 'retry', 'completed', 'failed')", name="ck_ingestion_jobs_valid_status"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_jobs"),
        sa.UniqueConstraint("document_id", name="uq_ingestion_jobs_document"),
    )
    op.create_index("ix_ingestion_jobs_status_available", "ingestion_jobs", ["status", "available_at"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_jobs_status_available", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
