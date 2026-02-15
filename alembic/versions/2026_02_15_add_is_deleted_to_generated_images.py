"""Add is_deleted flag to generated images

Revision ID: f8g9h0i1j2k3
Revises: f8a9b0c1d2e3
Create Date: 2026-02-15 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8g9h0i1j2k3"
down_revision: str | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add is_deleted column with default False for soft deletes
    op.add_column(
        "imagecreator_generated_images",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="0"),
    )

    # Create index on is_deleted for efficient filtering
    op.create_index(
        op.f("ix_imagecreator_generated_images_is_deleted"),
        "imagecreator_generated_images",
        ["is_deleted"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_imagecreator_generated_images_is_deleted"),
        table_name="imagecreator_generated_images",
    )
    op.drop_column("imagecreator_generated_images", "is_deleted")
