"""Add lookup support for tenant-scoped document filename validation.

Existing workspaces may already contain duplicate filenames, so enforcement is
kept in the upload transaction instead of creating a unique index that would
make this migration destructive or fail on existing data.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_unique_document_filename"
down_revision: Union[str, None] = "0004_user_password"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_documents_tenant_filename_ci",
        "documents",
        ["tenant_id", sa.text("lower(original_filename)")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_documents_tenant_filename_ci", table_name="documents")
