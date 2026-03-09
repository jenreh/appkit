"""add_inject_user_id_to_mcp_servers

Revision ID: e1f2a3b4c5d6
Revises: cad2e9f4g5h6
Create Date: 2026-03-09 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "cad2e9f4g5h6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add inject_user_id column to assistant_mcp_servers table."""
    op.add_column(
        "assistant_mcp_servers",
        sa.Column(
            "inject_user_id",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Remove inject_user_id column from assistant_mcp_servers table."""
    op.drop_column("assistant_mcp_servers", "inject_user_id")
