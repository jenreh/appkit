"""add email index on User nodes

Revision ID: 1975ea83b712
Revises: None
Create Date: 2026-05-30T14:00:00+00:00
"""
from datetime import datetime

message = "add email index on User nodes"
create_date = datetime.fromisoformat("2026-05-30T14:00:00+00:00")

revision = "1975ea83b712"
down_revision = None
branch_labels = []
depends_on = []
irreversible = False
snapshot = False


def upgrade(op) -> None:
    op.create_range_index("User", "email")
    op.create_range_index("User", "created_at")
    # Relationship index
    op.create_range_index("FOLLOWS", "since", rel=True)


def downgrade(op) -> None:
    op.drop_range_index("FOLLOWS", "since", rel=True)
    op.drop_range_index("User", "created_at")
    op.drop_range_index("User", "email")
