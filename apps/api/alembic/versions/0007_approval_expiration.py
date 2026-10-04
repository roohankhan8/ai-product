"""Add approval expiration and execution idempotency."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_approval_expiration"
down_revision: Union[str, None] = "0006_approval_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("approval_requests", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("approval_requests", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    op.execute(sa.text("UPDATE approval_requests SET expires_at = created_at + interval '1 hour', idempotency_key = id::text"))
    op.alter_column("approval_requests", "expires_at", nullable=False)
    op.alter_column("approval_requests", "idempotency_key", nullable=False)
    op.create_unique_constraint("uq_approval_requests_idempotency_key", "approval_requests", ["idempotency_key"])
    op.create_index("ix_approval_requests_tenant_expires", "approval_requests", ["tenant_id", "expires_at"])


def downgrade() -> None:
    op.drop_index("ix_approval_requests_tenant_expires", table_name="approval_requests")
    op.drop_constraint("uq_approval_requests_idempotency_key", "approval_requests", type_="unique")
    op.drop_column("approval_requests", "idempotency_key")
    op.drop_column("approval_requests", "expires_at")
