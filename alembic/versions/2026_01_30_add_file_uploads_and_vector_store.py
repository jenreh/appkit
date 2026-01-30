"""add_file_uploads_and_vector_store

Adds vector_store_id column to assistant_thread table and creates
assistant_file_uploads table for tracking files uploaded to OpenAI.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-30 10:00:00.000000

"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add vector_store_id column to assistant_thread table
    op.add_column(
        "assistant_thread",
        sa.Column("vector_store_id", sa.String(length=255), nullable=True),
    )

    # Create assistant_file_uploads table
    op.create_table(
        "assistant_file_uploads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("openai_file_id", sa.String(length=255), nullable=False),
        sa.Column("vector_store_id", sa.String(length=255), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["assistant_thread.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index(
        "ix_assistant_file_uploads_openai_file_id",
        "assistant_file_uploads",
        ["openai_file_id"],
        unique=False,
    )
    op.create_index(
        "ix_assistant_file_uploads_vector_store_id",
        "assistant_file_uploads",
        ["vector_store_id"],
        unique=False,
    )
    op.create_index(
        "ix_assistant_file_uploads_thread_id",
        "assistant_file_uploads",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_assistant_file_uploads_user_id",
        "assistant_file_uploads",
        ["user_id"],
        unique=False,
    )

    logger.info("Created assistant_file_uploads table and added vector_store_id column")


def downgrade() -> None:
    # Drop indexes
    op.drop_index(
        "ix_assistant_file_uploads_user_id",
        table_name="assistant_file_uploads",
    )
    op.drop_index(
        "ix_assistant_file_uploads_thread_id",
        table_name="assistant_file_uploads",
    )
    op.drop_index(
        "ix_assistant_file_uploads_vector_store_id",
        table_name="assistant_file_uploads",
    )
    op.drop_index(
        "ix_assistant_file_uploads_openai_file_id",
        table_name="assistant_file_uploads",
    )

    # Drop assistant_file_uploads table
    op.drop_table("assistant_file_uploads")

    # Remove vector_store_id column from assistant_thread
    op.drop_column("assistant_thread", "vector_store_id")

    logger.info("Removed assistant_file_uploads table and vector_store_id column")
