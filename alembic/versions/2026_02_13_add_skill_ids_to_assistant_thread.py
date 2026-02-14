"""Add skill_openai_ids to assistant_thread

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-02-13 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a9b0c1d2e3"
down_revision: str | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add skill_openai_ids column to assistant_thread table."""
    op.add_column(
        "assistant_thread",
        sa.Column(
            "skill_openai_ids",
            ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    """Remove skill_openai_ids column from assistant_thread table."""
    op.drop_column("assistant_thread", "skill_openai_ids")
