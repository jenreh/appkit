"""Add user prompts tables

Revision ID: 2026_02_01_add_user_prompts
Revises: a4b672c7b9d0
Create Date: 2026-02-01 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_02_01_user_prompts"
down_revision: str | None = "a4b672c7b9d0"  # Use the other head as the parent
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create assistant_user_prompts table (single table design)
    op.create_table(
        "assistant_user_prompts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("handle", sa.String(length=50), nullable=False),
        sa.Column(
            "description", sa.String(length=2000), nullable=False, server_default=""
        ),
        sa.Column("prompt_text", sa.String(length=20000), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_latest", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indices
    op.create_index(
        op.f("ix_assistant_user_prompts_user_id"),
        "assistant_user_prompts",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_prompt_lookup",
        "assistant_user_prompts",
        ["user_id", "handle"],
        unique=False,
    )
    op.create_index(
        "ix_user_prompt_listing",
        "assistant_user_prompts",
        ["user_id", "is_latest"],
        unique=False,
    )
    op.create_index(
        "ix_user_prompt_shared",
        "assistant_user_prompts",
        ["is_shared", "is_latest"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_prompt_shared", table_name="assistant_user_prompts")
    op.drop_index("ix_user_prompt_listing", table_name="assistant_user_prompts")
    op.drop_index("ix_user_prompt_lookup", table_name="assistant_user_prompts")
    op.drop_index(
        op.f("ix_assistant_user_prompts_user_id"),
        table_name="assistant_user_prompts",
    )
    op.drop_table("assistant_user_prompts")
