"""Add ai_model column to assistant_file_uploads.

Tracks which AI model (subscription / API key) was used to upload each
file so the file manager and cleanup service can operate per-subscription.

Revision ID: d2e3f4g5h6i7
Revises: c1d2e3f4g5h6
Create Date: 2026-02-21

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d2e3f4g5h6i7"
down_revision = "c1d2e3f4g5h6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ai_model column and backfill from thread relation."""
    # 1. Add nullable column first
    op.add_column(
        "assistant_file_uploads",
        sa.Column("ai_model", sa.String(length=100), nullable=True),
    )

    # 2. Backfill: copy ai_model from the associated assistant_thread
    op.execute(
        """
        UPDATE assistant_file_uploads f
        SET ai_model = t.ai_model
        FROM assistant_thread t
        WHERE f.thread_id = t.id
          AND t.ai_model IS NOT NULL
          AND t.ai_model != ''
        """
    )

    # 3. Set remaining NULLs to empty string
    op.execute(
        """
        UPDATE assistant_file_uploads
        SET ai_model = ''
        WHERE ai_model IS NULL
        """
    )

    # 4. Make column NOT NULL with default
    op.alter_column(
        "assistant_file_uploads",
        "ai_model",
        nullable=False,
        server_default="",
    )

    # 5. Add index for subscription-based queries
    op.create_index(
        "ix_assistant_file_uploads_ai_model",
        "assistant_file_uploads",
        ["ai_model"],
    )


def downgrade() -> None:
    """Remove ai_model column."""
    op.drop_index(
        "ix_assistant_file_uploads_ai_model",
        table_name="assistant_file_uploads",
    )
    op.drop_column("assistant_file_uploads", "ai_model")
