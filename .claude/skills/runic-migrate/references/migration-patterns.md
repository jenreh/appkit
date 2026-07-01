# Migration File Patterns

Annotated examples of common migration scenarios. Each pattern shows the full
module-level fields plus realistic `upgrade`/`downgrade` implementations.

---

## Pattern 1 — Initial migration (manually written)

The root migration has `down_revision = None`. It should create all indexes
and constraints your data model needs: indexes first in upgrade, constraints
before indexes in downgrade.

```python
# runic/versions/20250601_000001_initial_schema.py
from datetime import datetime

message = "initial schema"
create_date = datetime(2025, 6, 1, 0, 0, 0)
revision = "a1b2c3d4e5f6"
down_revision = None          # root — no parent
branch_labels = []
depends_on = []
irreversible = False
snapshot = False


def upgrade(op) -> None:
    # ── User ──────────────────────────────────────────────────────────────────
    op.create_range_index("User", "created_at")
    op.create_range_index("User", "email")
    # Unique constraint needs its backing range index created first
    op.create_constraint("UNIQUE", "NODE", "User", ["email"])

    # ── Post ──────────────────────────────────────────────────────────────────
    op.create_fulltext_index("Post", "title", "body", language="english")
    op.create_range_index("Post", "published_at")

    # ── Product ───────────────────────────────────────────────────────────────
    op.create_vector_index("Product", "embedding", 256, "cosine")

    # ── Roles (reference data) ────────────────────────────────────────────────
    op.seed(
        "MERGE (r:Role {name: row.name}) SET r.system = row.system",
        [{"name": "admin", "system": True}, {"name": "user", "system": False}],
    )


def downgrade(op) -> None:
    # Drop constraints BEFORE their backing indexes
    op.drop_constraint("UNIQUE", "NODE", "User", ["email"])
    op.drop_range_index("User", "email")
    op.drop_range_index("User", "created_at")
    op.drop_fulltext_index("Post", "title", "body")
    op.drop_range_index("Post", "published_at")
    op.drop_vector_index("Product", "embedding")
```

---

## Pattern 2 — Baseline-generated migration

`runic baseline -m 'baseline'` produces a file like this. The upgrade body
is the full live schema; downgrade reverses it in constraint-before-index order.
A comment flags vector indexes because the introspector uses `dimension=0` as a
placeholder — replace with the real value.

```python
# runic/versions/20250603_000001_baseline.py
from datetime import datetime

message = "baseline"
create_date = datetime(2025, 6, 3, 0, 0, 0)
revision = "ba5el1ne0000"
down_revision = None
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
    # verify options manually — dimension introspected as 0
    op.create_vector_index("Product", "embedding", 0, "cosine")
    op.create_constraint("UNIQUE", "NODE", "User", ["email"])


def downgrade(op) -> None:
    op.drop_constraint("UNIQUE", "NODE", "User", ["email"])
    op.drop_range_index("User", "email")
    op.drop_range_index("User", "created_at")
    op.drop_fulltext_index("Post", "title", "body")
    op.drop_range_index("Post", "published_at")
    op.drop_vector_index("Product", "embedding")
```

After baselining, replace `dimension=0` with the real vector size, then commit.

---

## Pattern 3 — Add a new property index in a follow-on migration

```python
# runic/versions/20250610_000002_add_article_indexes.py
from datetime import datetime

message = "add Article fulltext and range indexes"
create_date = datetime(2025, 6, 10, 0, 0, 0)
revision = "c3d4e5f6a7b8"
down_revision = "ba5el1ne0000"   # previous revision
branch_labels = []
depends_on = []
irreversible = False
snapshot = False


def upgrade(op) -> None:
    op.create_fulltext_index("Article", "title", "summary")
    op.create_range_index("Article", "published_at")


def downgrade(op) -> None:
    op.drop_fulltext_index("Article", "title", "summary")
    op.drop_range_index("Article", "published_at")
```

---

## Pattern 4 — Irreversible property rename with snapshot safety net

Set `irreversible = True` so runic refuses to downgrade unless `--force` is
passed. Set `snapshot = True` so runic copies the graph before running upgrade
and restores automatically on failure.

```python
# runic/versions/20250615_000003_rename_person_name.py
from datetime import datetime

message = "rename Person.name to full_name"
create_date = datetime(2025, 6, 15, 0, 0, 0)
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = []
depends_on = []
irreversible = True    # downgrade will fail unless --force is passed
snapshot = True        # graph copied before upgrade; restored on failure


def upgrade(op) -> None:
    # Batched rename: MATCH WHERE old IS NOT NULL AND new IS NULL pages at 10 000
    op.rename_property("Person", "name", "full_name")
    # Drop the old property on nodes already renamed (idempotent)
    op.run_cypher(
        "MATCH (p:Person) WHERE p.name IS NOT NULL REMOVE p.name"
    )


def downgrade(op) -> None:
    # Reached only with --force; data loss is possible if old property was dropped
    op.rename_property("Person", "full_name", "name")
```

---

## Pattern 5 — relabel_nodes with backend guard

`relabel_nodes` requires multi-label support. On Apache AGE or ArcadeDB it
raises `NotImplementedError`. Use it only when you know the target backend.

```python
# runic/versions/20250620_000004_relabel_member_to_user.py
from datetime import datetime

message = "rename Member nodes to User"
create_date = datetime(2025, 6, 20, 0, 0, 0)
revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = []
depends_on = []
irreversible = False
snapshot = True   # safety net: restore on failure


def upgrade(op) -> None:
    # Raises NotImplementedError on Apache AGE / ArcadeDB
    op.relabel_nodes("Member", "User")
    # Re-create the range index under the new label
    op.create_range_index("User", "email")


def downgrade(op) -> None:
    op.drop_range_index("User", "email")
    op.relabel_nodes("User", "Member")
```

---

## Pattern 6 — Mandatory constraint with data guard

Add a `MANDATORY` constraint only after confirming (or fixing) that all nodes
satisfy it. Use a Cypher guard in upgrade before creating the constraint.

```python
# runic/versions/20250625_000005_mandatory_user_email.py
from datetime import datetime

message = "enforce mandatory email on User"
create_date = datetime(2025, 6, 25, 0, 0, 0)
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = []
depends_on = []
irreversible = False
snapshot = False


def upgrade(op) -> None:
    # Back-fill a placeholder email so the constraint won't fail on create
    op.run_cypher(
        "MATCH (u:User) WHERE u.email IS NULL "
        "SET u.email = 'unknown+' + id(u) + '@example.com'"
    )
    # Range index must exist first (may already be there from initial migration)
    op.create_range_index("User", "email")
    op.create_constraint("MANDATORY", "NODE", "User", ["email"])


def downgrade(op) -> None:
    op.drop_constraint("MANDATORY", "NODE", "User", ["email"])
    # Leave the range index; removing it is a separate decision
```

---

## Pattern 7 — Seeding reference data in a follow-on migration

`op.seed` is idempotent: it uses MERGE so re-running it is safe.

```python
# runic/versions/20250630_000006_seed_categories.py
from datetime import datetime

message = "seed product categories"
create_date = datetime(2025, 6, 30, 0, 0, 0)
revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = []
depends_on = []
irreversible = False
snapshot = False

_CATEGORIES = [
    {"code": "books", "label": "Books"},
    {"code": "electronics", "label": "Electronics"},
    {"code": "clothing", "label": "Clothing"},
]


def upgrade(op) -> None:
    op.create_range_index("Category", "code")
    op.create_constraint("UNIQUE", "NODE", "Category", ["code"])
    op.seed(
        "MERGE (c:Category {code: row.code}) SET c.label = row.label",
        _CATEGORIES,
    )


def downgrade(op) -> None:
    op.run_cypher("MATCH (c:Category) DETACH DELETE c")
    op.drop_constraint("UNIQUE", "NODE", "Category", ["code"])
    op.drop_range_index("Category", "code")
```

---

## Ordering rules — quick reference

| Operation order | upgrade | downgrade |
| --- | --- | --- |
| Indexes vs constraints | indexes **first** | constraints **first** |
| Multiple indexes | any order | any order |
| relabel then index on new label | relabel **first** | drop index **first** |
| Data migration vs schema | data ops **last** (after structural changes) | data ops **first** |

---

## Field annotation → op.* translation table

| OGM Field annotation | upgrade call(s) | downgrade call(s) |
| --- | --- | --- |
| `Field(index=True)` | `create_range_index(label, prop)` | `drop_range_index(label, prop)` |
| `Field(unique=True)` | `create_range_index` then `create_constraint("UNIQUE", ...)` | `drop_constraint("UNIQUE", ...)` then `drop_range_index` |
| `Field(index_type="FULLTEXT")` | `create_fulltext_index(label, *props)` | `drop_fulltext_index(label, *props)` |
| `Field(index_type="VECTOR")` | `create_vector_index(label, prop, dim, sim)` | `drop_vector_index(label, prop)` |
| No index annotation | *(no op.* call needed)* | — |
