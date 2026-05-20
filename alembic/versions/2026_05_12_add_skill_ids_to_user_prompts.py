"""Add skill_ids to user prompts

Revision ID: a1b2c3d4e5f7
Revises: f2b5b9c0d1e2
Create Date: 2026-05-12 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: str | None = "f2b5b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assistant_user_prompts",
        sa.Column(
            "skill_ids",
            ARRAY(sa.Integer()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("assistant_user_prompts", "skill_ids")
