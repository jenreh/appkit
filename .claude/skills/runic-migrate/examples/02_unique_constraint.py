"""add unique email constraint on User

Revision ID: ae1027a6acf0
Revises: 1975ea83b712
Create Date: 2026-05-30T15:00:00+00:00
"""
from datetime import datetime

message = "add unique email constraint on User"
create_date = datetime.fromisoformat("2026-05-30T15:00:00+00:00")

revision = "ae1027a6acf0"
down_revision = "1975ea83b712"
branch_labels = []
depends_on = []
irreversible = False
snapshot = False


def upgrade(op) -> None:
    # Range index must exist before creating a UNIQUE constraint.
    # create_constraint("UNIQUE", ...) auto-creates the backing index if missing
    # and polls until status reaches OPERATIONAL.
    op.create_constraint("UNIQUE", "NODE", "User", ["email"])
    op.create_constraint("MANDATORY", "NODE", "User", ["email"])


def downgrade(op) -> None:
    # Always drop constraints BEFORE the backing index, or FalkorDB will refuse.
    op.drop_constraint("MANDATORY", "NODE", "User", ["email"])
    op.drop_constraint("UNIQUE", "NODE", "User", ["email"])
