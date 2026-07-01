"""seed role reference data + example merge revision

Revision ID: e5f6789abcde
Revises: d4e5f6789abc
Create Date: 2026-05-30T18:00:00+00:00
"""
from datetime import datetime

message = "seed role reference data"
create_date = datetime.fromisoformat("2026-05-30T18:00:00+00:00")

revision = "e5f6789abcde"
down_revision = "d4e5f6789abc"
branch_labels = []
depends_on = []
irreversible = False
snapshot = False

_ROLES = [
    {"name": "admin",   "system": True},
    {"name": "editor",  "system": True},
    {"name": "viewer",  "system": True},
]


def upgrade(op) -> None:
    # seed() wraps UNWIND $rows AS row <merge_query> — idempotent on re-run
    op.seed(
        "MERGE (r:Role {name: row.name}) SET r.system = row.system",
        _ROLES,
    )


def downgrade(op) -> None:
    names = [r["name"] for r in _ROLES]
    op.run_cypher(
        "MATCH (r:Role) WHERE r.name IN $names AND r.system = true DETACH DELETE r",
        {"names": names},
    )


# ---------------------------------------------------------------------------
# How a MERGE revision looks (two heads → one)
# ---------------------------------------------------------------------------
# When two branches diverge from the same head, resolve them:
#
#   runic heads
#   runic merge <rev_a> <rev_b> -m "merge feature-x into main"
#
# The generated file has a tuple down_revision:
#
#   revision = "f6789abcdef0"
#   down_revision = ("rev_a_id", "rev_b_id")   # ← tuple, not string
#
#   def upgrade(op) -> None:
#       pass   # add reconciliation ops if needed
#
#   def downgrade(op) -> None:
#       pass
