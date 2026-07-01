---
name: runic-migrate
description: |
  Expert guide for runic — an Alembic-style graph schema migration tool that
  supports FalkorDB, Memgraph, Neo4j, ArcadeDB, and Apache AGE. Use whenever
  the user works with runic: CLI commands, migration file anatomy, op.* API,
  env.py config, autogenerate, branching/merge, or testing. Invoke for any
  versions/*.py file, `runic` CLI question, or graph schema change task.
---

# Runic — Graph Schema Migration Tool

Runic is an Alembic-style migration framework for graph databases (FalkorDB,
Memgraph, Neo4j, ArcadeDB, Apache AGE). It tracks schema versions in a version
node inside each graph and drives upgrades/downgrades via Python scripts stored
in `versions/`.

- FalkorDB version node label: `(:_FalkorMigrateVersion)`
- All other backends: `(:_RunicMigrateVersion)`

For real migration file examples see [examples/](examples/).
For the full `op.*` API and `SchemaManifest` see [references/op-api.md](references/op-api.md).
For autogenerate, programmatic SDK, testing, and branching see [references/advanced.md](references/advanced.md).
For the initial migration workflow (dev bootstrap → baseline → production) see [references/initial-migration.md](references/initial-migration.md).
For annotated migration patterns (rename, relabel, seed, constraint guard) see [references/migration-patterns.md](references/migration-patterns.md).

---

## Quick-start

```bash
pip install runic          # or: uv add runic

runic init                 # scaffold runic/ directory
# edit runic/env.py to point at your graph database instance
runic revision -m "create user index"
# edit the generated versions/*.py (see examples/ for patterns)
runic upgrade head
```

---

## Directory layout (after `runic init`)

```
runic/
├── env.py            # executed on every CLI call; configures adapter + context
├── script.py.mako    # Mako template for new revision files
└── versions/
    ├── .gitkeep
    └── <rev_id>_<slug>.py
```

Default config: `runic/env.py` — override with `--config path/to/env.py`.

When you init to a non-default location, runic writes a `.runic` file in the
working directory containing the path to `env.py`. Subsequent commands use this
as a fallback when the default `runic/env.py` does not exist. Commit `.runic`.

---

## env.py

```python
import os
from runic.migrate import context
from runic.migrate.adapters import create_adapter

adapter = create_adapter(
    "falkordb",
    url=os.getenv("FALKORDB_URL", "falkor://localhost:6379"),
    graph_name=os.getenv("FALKORDB_GRAPH", "my_graph"),
)
context.configure(adapter)
```

For autogenerate/check, add `target_manifest` — see [references/advanced.md](references/advanced.md).

---

## CLI reference

| Command | Description |
|---|---|
| `runic init [DIR]` | Scaffold migration environment (default: `runic/`); `--force` to overwrite |
| `runic revision -m "msg"` | Create new empty revision at current head |
| `runic revision -m "msg" --autogenerate` | Diff manifest vs live; emit candidate ops |
| `runic revision -m "msg" --branch-label LABEL` | Create revision on a named branch |
| `runic revision -m "msg" --format` | Auto-format the generated file with ruff |
| `runic upgrade [TARGET]` | Apply upgrades to TARGET (default: `head`) |
| `runic upgrade TARGET --preview` | Print ops without executing |
| `runic upgrade TARGET --validate-on-migrate` | Abort if any applied script has a checksum mismatch |
| `runic upgrade TARGET --installed-by NAME` | Record attribution with each applied revision |
| `runic downgrade TARGET` | Revert to TARGET (`base`, `-1`, rev id) |
| `runic downgrade TARGET --force` | Revert through `irreversible` revisions |
| `runic current` | Show applied revision |
| `runic history` | List all revisions newest-first |
| `runic history --verbose` | Include create_date and down_revision; mark branch points |
| `runic history --range start:end` | Slice of history |
| `runic heads` | List all head revisions (multiple = branched) |
| `runic branches` | List branch-point revisions |
| `runic stamp TARGET` | Set version pointer without running migrations |
| `runic stamp base --purge` | Clear version pointer |
| `runic show REV` | Print full metadata for a revision |
| `runic test REV` | Round-trip test: upgrade → downgrade → upgrade |
| `runic test REV --url URL --graph NAME` | Same against an explicit DB |
| `runic merge R1 R2 -m "msg"` | Create merge revision for two heads |
| `runic check` | CI gate: non-zero exit if manifest has pending changes |
| `runic validate` | Verify applied scripts match their stored checksums |
| `runic run FILE.py [FILE.py ...]` | Execute `.py` migration script(s) (must have `upgrade(op)`) against the DB without recording in the chain |
| `runic info` | Show migration status: current, applied, pending counts (COMPARE mode) |
| `runic info --mode LOCAL` | Offline-only: local revision count and heads |
| `runic info --mode REMOTE` | DB-only: which revision is applied |
| `runic baseline [-m "msg"]` | Introspect live schema, write a root revision, and stamp it |
| `runic baseline --stamp-only` | Stamp the version node only, without writing a file |

**Relative targets:** `+1` / `+2` (upgrade N steps), `-1` / `-2` (downgrade N steps).

---

## Migration file anatomy

```python
"""create user email index

Revision ID: 1975ea83b712
Revises: None
Create Date: 2026-05-30T14:00:00+00:00
"""
from datetime import UTC, datetime

message = "create user email index"
create_date = datetime.fromisoformat("2026-05-30T14:00:00+00:00")

revision = "1975ea83b712"
down_revision = None       # None = base; str = parent id; tuple = merge revision
branch_labels = []
depends_on = []
irreversible = False       # True → refuse downgrade unless --force
snapshot = False           # True → GRAPH.COPY before upgrade; restore on failure


def upgrade(op) -> None:
    op.create_range_index("User", "email")
    op.create_constraint("UNIQUE", "NODE", "User", ["email"])


def downgrade(op) -> None:
    op.drop_constraint("UNIQUE", "NODE", "User", ["email"])  # constraint BEFORE index
    op.drop_range_index("User", "email")
```

**Key rules:**
- Drop constraints **before** dropping their backing range index in `downgrade`.
- Create the range index **before** a unique constraint on the same property in `upgrade`.
- Use `irreversible = True` for one-way data migrations (e.g. rename + drop old property).
- Use `snapshot = True` for risky data migrations; runic `GRAPH.COPY`s before upgrade and restores on failure/downgrade.
- Keep every data step **idempotent** — use `MERGE` / guarded `WHERE … IS NULL` writes; graph databases have no multi-statement transactions.

---

For the full `op.*` API signatures, see [references/op-api.md](references/op-api.md).
