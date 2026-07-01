"""
Example: migration produced by `runic baseline -m 'baseline'`.

runic baseline introspects the live graph and auto-generates a root migration
that recreates the full schema.  The file is stamped as already applied, so
runic never re-executes it on existing environments — only fresh deployments
run it via `runic upgrade head`.

Key differences from a hand-written initial migration:
- down_revision is always None (this is the root of the chain)
- vector indexes get `# verify options manually` because the introspector
  records dimension=0 as a placeholder; replace with the real value
- op.* ordering is enforced: indexes before constraints in upgrade,
  constraints before indexes in downgrade

After running `runic baseline`:
1. Edit any `dimension=0` vector index calls with the real dimension.
2. Paste the printed SchemaManifest snippet into env.py if you want autogenerate.
3. Commit the generated file alongside the .runic marker (if non-default location).
"""

from datetime import datetime

message = "baseline"
create_date = datetime(2025, 6, 3, 12, 0, 0)
revision = "ba5el1ne0000"
down_revision = None          # root: no parent revision
branch_labels = []
depends_on = []
irreversible = False
snapshot = False


def upgrade(op) -> None:
    # ── Introspected from live graph — indexes first, then constraints ─────────
    op.create_range_index("User", "created_at")
    op.create_range_index("User", "email")

    op.create_fulltext_index("Post", "title", "body")
    op.create_range_index("Post", "published_at")

    # verify options manually — dimension introspected as 0; replace with real value
    op.create_vector_index("Product", "embedding", 0, "cosine")

    # Constraints must come after their backing range indexes
    op.create_constraint("UNIQUE", "NODE", "User", ["email"])


def downgrade(op) -> None:
    # Constraints first, then their backing indexes
    op.drop_constraint("UNIQUE", "NODE", "User", ["email"])

    op.drop_range_index("User", "email")
    op.drop_range_index("User", "created_at")

    op.drop_fulltext_index("Post", "title", "body")
    op.drop_range_index("Post", "published_at")

    op.drop_vector_index("Product", "embedding")
