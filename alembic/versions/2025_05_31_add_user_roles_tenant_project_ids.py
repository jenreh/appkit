"""Add roles, tenant_ids, and project_ids to User table

Revision ID: 8bcdef012345
Revises: 1a2b3c4d5e6f
Create Date: 2025-05-31

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from alembic import op

# revision identifiers, used by Alembic
revision = "8bcdef012345"
down_revision = "1a2b3c4d5e6f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add roles, tenant_ids, and project_ids columns to oauth_user table."""
    # Add roles column
    op.add_column(
        "oauth_user",
        sa.Column(
            "roles",
            ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )

    # Add tenant_ids column
    op.add_column(
        "oauth_user",
        sa.Column(
            "tenant_ids",
            ARRAY(sa.Integer()),
            nullable=False,
            server_default="{}",
        ),
    )

    # Add project_ids column
    op.add_column(
        "oauth_user",
        sa.Column(
            "project_ids",
            ARRAY(sa.Integer()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    """Remove roles, tenant_ids, and project_ids columns from oauth_user table."""
    op.drop_column("oauth_user", "project_ids")
    op.drop_column("oauth_user", "tenant_ids")
    op.drop_column("oauth_user", "roles")
