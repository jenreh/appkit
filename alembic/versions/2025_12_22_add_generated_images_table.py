"""add_generated_images_table

Revision ID: 4a5b6c7d8e9f
Revises: 2ad7a1d57f3d
Create Date: 2025-12-22 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4a5b6c7d8e9f"
down_revision: str | None = "2ad7a1d57f3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "imagecreator_generated_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("prompt", sa.String(length=4000), nullable=False),
        sa.Column("style", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("quality", sa.String(length=20), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_imagecreator_generated_images_user_id"),
        "imagecreator_generated_images",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_imagecreator_generated_images_created_at"),
        "imagecreator_generated_images",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_imagecreator_generated_images_created_at"),
        table_name="imagecreator_generated_images",
    )
    op.drop_index(
        op.f("ix_imagecreator_generated_images_user_id"),
        table_name="imagecreator_generated_images",
    )
    op.drop_table("imagecreator_generated_images")
