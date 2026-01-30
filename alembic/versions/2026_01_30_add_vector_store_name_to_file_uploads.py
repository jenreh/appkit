"""add_vector_store_name_to_file_uploads

Revision ID: 39e2ac102b93
Revises: c3d4e5f6a7b8
Create Date: 2026-01-30 17:41:13.468603

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "39e2ac102b93"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assistant_file_uploads",
        sa.Column(
            "vector_store_name", sa.String(255), nullable=False, server_default=""
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_file_uploads", "vector_store_name")
