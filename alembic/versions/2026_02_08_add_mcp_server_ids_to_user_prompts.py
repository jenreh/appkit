"""Add mcp_server_ids to user prompts

Revision ID: c5d6e7f8a9b0
Revises: bah25gab8c9a
Create Date: 2026-02-08 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8a9b0"
down_revision: str | None = "bah25gab8c9a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assistant_user_prompts",
        sa.Column(
            "mcp_server_ids",
            ARRAY(sa.Integer()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_user_prompts", "mcp_server_ids")
