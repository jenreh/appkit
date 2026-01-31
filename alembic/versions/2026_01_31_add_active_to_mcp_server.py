"""add_active_to_mcp_server

Add active boolean field to assistant_mcp_servers table to allow
enabling/disabling MCP servers without deleting them.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-01-31 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "39e2ac102b93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add active column to assistant_mcp_servers table."""
    op.add_column(
        "assistant_mcp_servers",
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    """Remove active column from assistant_mcp_servers table."""
    op.drop_column("assistant_mcp_servers", "active")
