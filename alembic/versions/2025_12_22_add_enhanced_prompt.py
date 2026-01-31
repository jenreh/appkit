"""add_enhanced_prompt_to_generated_images

Revision ID: 5b6c7d8e9f0a
Revises: 4a5b6c7d8e9f
Create Date: 2025-12-22 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b6c7d8e9f0a"
down_revision: str | None = "4a5b6c7d8e9f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "imagecreator_generated_images",
        sa.Column("enhanced_prompt", sa.String(length=8000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("imagecreator_generated_images", "enhanced_prompt")
