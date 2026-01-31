"""add_is_uploaded_to_generated_images

Revision ID: a1b2c3d4e5f6
Revises: 5b6c7d8e9f0a
Create Date: 2026-01-02 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "5b6c7d8e9f0a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add is_uploaded column with default False
    op.add_column(
        "imagecreator_generated_images",
        sa.Column("is_uploaded", sa.Boolean(), nullable=False, server_default="0"),
    )

    # Create index on is_uploaded for efficient filtering
    op.create_index(
        op.f("ix_imagecreator_generated_images_is_uploaded"),
        "imagecreator_generated_images",
        ["is_uploaded"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_imagecreator_generated_images_is_uploaded"),
        table_name="imagecreator_generated_images",
    )
    op.drop_column("imagecreator_generated_images", "is_uploaded")
