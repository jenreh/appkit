"""add_assistant_thread_table

Revision ID: db3b5623e5a4
Revises: 20251207_openai_agents
Create Date: 2025-12-07 22:48:11.831752

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "db3b5623e5a4"
down_revision: str | None = "20251207_openai_agents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assistant_thread",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("ai_model", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("messages", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_assistant_thread_thread_id"),
        "assistant_thread",
        ["thread_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_assistant_thread_user_id"),
        "assistant_thread",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_assistant_thread_user_id"), table_name="assistant_thread")
    op.drop_index(op.f("ix_assistant_thread_thread_id"), table_name="assistant_thread")
    op.drop_table("assistant_thread")
