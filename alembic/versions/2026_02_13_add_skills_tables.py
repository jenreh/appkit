"""Add skills tables

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-02-13 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: str | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_skills",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "openai_id",
            sa.String(length=255),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True, default=""),
        sa.Column(
            "default_version",
            sa.String(length=20),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "latest_version",
            sa.String(length=20),
            nullable=False,
            server_default="1",
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("required_role", sa.String(), nullable=True),
        sa.Column(
            "last_synced",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "assistant_user_skill_selections",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column(
            "skill_openai_id",
            sa.String(length=255),
            nullable=False,
            index=True,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.create_index(
        "ix_user_skill_unique",
        "assistant_user_skill_selections",
        ["user_id", "skill_openai_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_skill_unique",
        table_name="assistant_user_skill_selections",
    )
    op.drop_table("assistant_user_skill_selections")
    op.drop_table("assistant_skills")
