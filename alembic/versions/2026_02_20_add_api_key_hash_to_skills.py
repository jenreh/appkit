"""Add api_key_hash column to assistant_skills.

Revision ID: c1d2e3f4g5h6
Revises: f3g4h5i6j7k8
Create Date: 2026-02-20

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c1d2e3f4g5h6"
down_revision = "f3g4h5i6j7k8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add api_key_hash column to assistant_skills table."""
    op.add_column(
        "assistant_ai_models",
        sa.Column(
            "enable_tracking",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "assistant_skills",
        sa.Column("api_key_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_assistant_skills_api_key_hash",
        "assistant_skills",
        ["api_key_hash"],
    )


def downgrade() -> None:
    """Remove api_key_hash column from assistant_skills table."""
    op.drop_index(
        "ix_assistant_skills_api_key_hash",
        table_name="assistant_skills",
    )
    op.drop_column("assistant_skills", "api_key_hash")
    op.drop_column("assistant_ai_models", "enable_tracking")
