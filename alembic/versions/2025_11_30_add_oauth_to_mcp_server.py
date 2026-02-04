"""Add OAuth / discovery fields to MCP server.

Revision ID: 4afe63b2d1c0
Revises: 5f4e3d2c1b0a
Create Date: 2025-11-30 14:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4afe63b2d1c0"  # 20251130_add_oauth_to_mcp_server
down_revision: str | None = "5f4e3d2c1b0a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add OAuth / discovery columns to mcp_server table."""
    op.add_column(
        "mcp_server",
        sa.Column(
            "auth_type", sa.String(length=32), nullable=False, server_default="none"
        ),
    )
    op.add_column(
        "mcp_server",
        sa.Column("discovery_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "mcp_server",
        sa.Column("oauth_issuer", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "mcp_server",
        sa.Column("oauth_authorize_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "mcp_server",
        sa.Column("oauth_token_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "mcp_server",
        sa.Column("oauth_scopes", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "mcp_server",
        sa.Column("oauth_discovered_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Remove server_default after data migration so new rows must set auth_type explicitly or use ORM default
    op.alter_column("mcp_server", "auth_type", server_default=None)


def downgrade() -> None:
    """Remove OAuth / discovery columns from mcp_server table."""
    op.drop_column("mcp_server", "oauth_discovered_at")
    op.drop_column("mcp_server", "oauth_scopes")
    op.drop_column("mcp_server", "oauth_token_url")
    op.drop_column("mcp_server", "oauth_authorize_url")
    op.drop_column("mcp_server", "oauth_issuer")
    op.drop_column("mcp_server", "discovery_url")
    op.drop_column("mcp_server", "auth_type")
