"""add required_role to mcp server

Revision ID: a4b672c7b9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-04 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4b672c7b9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assistant_mcp_servers", sa.Column("required_role", sa.String(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("assistant_mcp_servers", "required_role")
