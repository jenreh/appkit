"""rename Person.name to full_name — irreversible data migration

Revision ID: c3d4e5f67890
Revises: ae1027a6acf0
Create Date: 2026-05-30T16:00:00+00:00
"""
from datetime import datetime

message = "rename Person.name to full_name — irreversible data migration"
create_date = datetime.fromisoformat("2026-05-30T16:00:00+00:00")

revision = "c3d4e5f67890"
down_revision = "ae1027a6acf0"
branch_labels = []
depends_on = []
irreversible = True   # downgrade blocked unless --force
snapshot = True       # GRAPH.COPY before upgrade; auto-restore on failure


def upgrade(op) -> None:
    # rename_property is batched (default 10 000 nodes per query) and idempotent —
    # safe to re-run if the migration fails partway through.
    op.rename_property("Person", "name", "full_name")
    # Drop the old property after confirming the rename is complete.
    op.run_cypher(
        "MATCH (p:Person) WHERE p.name IS NOT NULL REMOVE p.name"
    )
    # Re-index the new property name.
    op.create_range_index("Person", "full_name")


def downgrade(op) -> None:
    # Data is gone; runic will restore the GRAPH.COPY snapshot automatically
    # when snapshot=True is set. Explicit downgrade is not possible.
    raise NotImplementedError(
        "irreversible — runic will restore the pre-migration snapshot"
    )
