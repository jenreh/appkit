"""add_name_to_bpmn_diagrams

Revision ID: f2b5b9c0d1e2
Revises: f7a8b9c0d1e2
Create Date: 2026-03-15 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2b5b9c0d1e2"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add name column to mcp_bpmn_diagrams.

    Populates existing rows from prompt (truncated to 128 chars) or
    a default of 'Diagram <first 8 chars of diagram_id>'.
    """
    # Add column as nullable first for data migration
    op.add_column(
        "mcp_bpmn_diagrams",
        sa.Column("name", sa.String(length=128), nullable=True),
    )

    # Populate existing rows
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE mcp_bpmn_diagrams
            SET name = CASE
                WHEN prompt IS NOT NULL AND TRIM(prompt) != ''
                    THEN SUBSTR(TRIM(prompt), 1, 128)
                ELSE 'Diagram ' || SUBSTR(diagram_id, 1, 8)
            END
            WHERE name IS NULL
            """
        )
    )

    # Now make column NOT NULL
    op.alter_column(
        "mcp_bpmn_diagrams",
        "name",
        nullable=False,
    )


def downgrade() -> None:
    """Remove name column from mcp_bpmn_diagrams."""
    op.drop_column("mcp_bpmn_diagrams", "name")
