# Runic — Advanced Topics

---

## Autogenerate

Requires `target_manifest` in `env.py` (see [op-api.md](op-api.md#schemamnanifest-for-autogenerate--check)).

```bash
runic revision -m "add user indexes" --autogenerate
```

Runic introspects the live graph via `CALL db.indexes()` and `CALL db.constraints()`,
diffs against the manifest, and writes candidate `op.*` calls into the revision.
Always review and edit the generated file before applying.

**CI gate — fail if schema is out of sync:**

```bash
runic check   # exits 1 with a summary of pending ops; exits 0 if up-to-date
```

---

## Programmatic SDK

```python
from pathlib import Path
from runic import Runic, init
from runic.migrate.adapters import create_adapter

# One-time: scaffold the migration directory
init(Path("runic/"))

adapter = create_adapter(
    "falkordb",
    url="falkor://localhost:6379",
    graph_name="my_graph",
)
runic = Runic(adapter, script_location=Path("runic/"))

runic.migrate.upgrade("head")
runic.migrate.downgrade("base")
runic.migrate.stamp("head")

print(runic.migrate.current())          # currently applied revision id or None
print(runic.migrate.get_history())      # list[RevisionInfo], newest first
print(runic.migrate.get_heads())        # list[Revision]

# Create a revision programmatically
path = runic.migrate.create_revision("add index", branch_labels=["feature-x"])

# Inspect a revision
rev = runic.migrate.show_revision("1975ea")   # prefix lookup
```

`Runic` also accepts `preview=True` (dry-run) and `target_manifest=...` (autogenerate).

---

## Testing a migration

`runic test <rev>` runs upgrade → downgrade → upgrade on an ephemeral copy of
the graph and reports entity / index / constraint counts at each phase. The
ephemeral graph is deleted on exit.

```bash
runic test 1975ea83b712

# against an explicit DB (no env.py needed)
runic test 1975ea83b712 --url falkor://localhost:6379 --graph myapp
```

Output:
```
runic test 1975ea83b712
─────────────────────────────────────────────
Phase A (upgrade):    ✓  nodes=0  indices=1  constraints=1
Phase B (downgrade):  ✓  nodes=0  indices=0  constraints=0
Phase C (idempotency):✓  nodes=0  indices=1  constraints=1
─────────────────────────────────────────────
PASSED
```

### Using falkordblite for CI (no server required)

```python
import falkordblite
from runic import Runic
from runic.migrate.adapters.falkordb import FalkorDBAdapter

db = falkordblite.FalkorDB()
adapter = FalkorDBAdapter(db, db.select_graph("ci_test"))
runic = Runic(adapter, script_location=Path("runic/"))
runic.migrate.upgrade("head")
```

---

## Branching and merge

When two developers each create a revision off the same head, runic detects
multiple heads. Resolve with a merge revision:

```bash
runic heads                            # lists both heads
runic merge <rev1> <rev2> -m "merge feature-x and main"
runic upgrade head
```

A merge revision has `down_revision = ("rev1_id", "rev2_id")` — a tuple.
The merge script body is empty by default; add any reconciliation ops needed.

**Example merge file:**

```python
revision = "ab12cd34ef56"
down_revision = ("1975ea83b712", "9f3c8b2a1d04")  # both parents
branch_labels = []
depends_on = []
irreversible = False
snapshot = False

def upgrade(op) -> None:
    pass   # add any reconciliation ops here

def downgrade(op) -> None:
    pass
```

### depends_on

Use `depends_on` (list of revision ids) to express an ordering dependency
without making a revision a `down_revision` parent — useful across independent
migration streams.

---

## Common patterns

### Safe irreversible data migration

```python
irreversible = True
snapshot = True          # GRAPH.COPY before upgrade; restore on failure/downgrade

def upgrade(op) -> None:
    op.rename_property("Person", "name", "full_name")
    op.run_cypher("MATCH (p:Person) REMOVE p.name")   # drop old property

def downgrade(op) -> None:
    raise NotImplementedError("irreversible — restore from snapshot or backup")
```

### Seeding reference data idempotently

```python
def upgrade(op) -> None:
    op.seed(
        "MERGE (r:Role {name: row.name}) SET r.builtin = true",
        [{"name": "admin"}, {"name": "viewer"}, {"name": "editor"}],
    )

def downgrade(op) -> None:
    op.run_cypher(
        "MATCH (r:Role) WHERE r.name IN $names AND r.builtin = true DETACH DELETE r",
        {"names": ["admin", "viewer", "editor"]},
    )
```

### Baselining an existing database

When adding runic to a graph that already has indexes/constraints:

```bash
# 1. Create a revision that reflects current state (upgrade is a no-op)
runic revision -m "baseline"
# 2. Stamp the database without running it
runic stamp <rev_id>
```
