"""add_prompt_to_mcp_server

Revision ID: 5f4e3d2c1b0a
Revises: 4de8db9a8e68
Create Date: 2025-11-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5f4e3d2c1b0a"
down_revision: str | None = "4de8db9a8e68"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add prompt column to mcp_server table."""
    op.add_column(
        "mcp_server",
        sa.Column("prompt", sa.String(length=2000), nullable=True),
    )


def downgrade() -> None:
    """Remove prompt column from mcp_server table."""
    op.drop_column("mcp_server", "prompt")
