"""add_bpmn_diagrams_table

Revision ID: f7a8b9c0d1e2
Revises: e1f2a3b4c5d6
Create Date: 2026-03-09 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "abc123def456"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create bpmn_diagrams table."""
    op.create_table(
        "mcp_bpmn_diagrams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("diagram_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("xml_content", sa.LargeBinary(), nullable=False),
        sa.Column("prompt", sa.String(length=8000), nullable=True),
        sa.Column(
            "diagram_type",
            sa.String(length=50),
            nullable=False,
            server_default="process",
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mcp_bpmn_diagrams_id"), "mcp_bpmn_diagrams", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_mcp_bpmn_diagrams_diagram_id"),
        "mcp_bpmn_diagrams",
        ["diagram_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_mcp_bpmn_diagrams_user_id"),
        "mcp_bpmn_diagrams",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_mcp_bpmn_diagrams_user_created",
        "mcp_bpmn_diagrams",
        ["user_id", "created"],
        unique=False,
    )
    op.create_index(
        "ix_mcp_bpmn_diagrams_is_deleted",
        "mcp_bpmn_diagrams",
        ["is_deleted"],
        unique=False,
    )


def downgrade() -> None:
    """Drop bpmn_diagrams table."""
    op.drop_index("ix_mcp_bpmn_diagrams_is_deleted", table_name="mcp_bpmn_diagrams")
    op.drop_index("ix_mcp_bpmn_diagrams_user_created", table_name="mcp_bpmn_diagrams")
    op.drop_index(op.f("ix_mcp_bpmn_diagrams_user_id"), table_name="mcp_bpmn_diagrams")
    op.drop_index(
        op.f("ix_mcp_bpmn_diagrams_diagram_id"), table_name="mcp_bpmn_diagrams"
    )
    op.drop_index(op.f("ix_mcp_bpmn_diagrams_id"), table_name="mcp_bpmn_diagrams")
    op.drop_table("mcp_bpmn_diagrams")
