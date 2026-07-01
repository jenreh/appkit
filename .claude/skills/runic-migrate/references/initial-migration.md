# Initial Migration Workflow

How to get from "no schema version history" to a fully managed runic migration
chain — covering development bootstrap, baselining an existing graph, and
writing explicit initial migrations.

---

## The three starting situations

| You have… | Best approach |
| --- | --- |
| A fresh project, no live data | Write an explicit initial migration |
| A live graph bootstrapped with `SchemaManager` (or by hand) | Use `runic baseline` |
| A live graph with no idea what's in it | Use `runic baseline` |

---

## Stage 1 — Development bootstrap with SchemaManager (no migration needed)

`SchemaManager` reads index declarations directly from OGM model `Field`
annotations and issues the required adapter DDL. Use it to get a local dev
graph up to speed instantly, without writing a migration:

```python
# scripts/bootstrap_schema.py — run once per dev environment, not in production
from runic.migrate import SchemaManager, create_adapter
from myapp.models import User, Post, Article, KnowsEdge

adapter = create_adapter(
    "falkordb",
    url="falkor://localhost:6379",
    graph_name="myapp_dev",
)
schema = SchemaManager(adapter)

# Creates all indexes declared on your models (Field(index=True),
# Field(unique=True), Field(index_type='FULLTEXT/VECTOR'))
schema.sync_schema([User, Post, Article, KnowsEdge])

# Optionally check what ended up in the graph
print(schema.get_schema_diff([User, Post, Article, KnowsEdge]))
```

`sync_schema` skips specs that already exist, so it is safe to call repeatedly.

**What models it reads**: Field annotations on OGM `Node`/`Edge` subclasses:

```python
from runic.ogm import Node, Field

class User(Node, labels=["User"]):
    id: str = Field(primary_key=True)
    email: str = Field(unique=True)          # → UNIQUE constraint + RANGE index
    name: str = Field(index=True)            # → RANGE index
    bio: str = Field(index_type="FULLTEXT")  # → FULLTEXT index
    embedding: list[float] = Field(index_type="VECTOR", default=None)
```

---

## Stage 2 — Baseline an existing graph

Once the schema is stable and ready for version control, capture it with
`runic baseline`. This introspects the live graph, writes a root migration file
(see [example 06](../examples/06_baseline_generated.py)), and stamps the version
node — so runic treats it as already applied.

```bash
# One-time: scaffold the runic directory if not done yet
runic init

# Introspect the live graph, generate the initial migration, and stamp it
runic baseline -m "initial schema"

# View the generated file
runic show <rev_id>
```

After running, `runic baseline` also prints a ready-to-paste `SchemaManifest`
block for your `env.py`:

```
Schema manifest — paste into env.py and pass to context.configure(...)
────────────────────────────────────────────────────────────────────
from runic.migrate.manifest import RangeIndex, UniqueConstraint, SchemaManifest

target_manifest = SchemaManifest(
    range_indexes=[
        RangeIndex(label='User', prop='email'),
        RangeIndex(label='User', prop='name'),
    ],
    fulltext_indexes=[],
    vector_indexes=[],
    constraints=[
        UniqueConstraint(entity='NODE', label='User', props=['email']),
    ],
)
────────────────────────────────────────────────────────────────────
```

Paste it into `env.py` and add `target_manifest=target_manifest` to your
`context.configure(...)` call to enable `runic revision --autogenerate` going
forward.

---

## Stage 3 — Adding schema changes as versioned migrations

From this point on, write explicit migration scripts for every schema change:

```bash
runic revision -m "add Article fulltext index"
# edit the generated file
runic upgrade head
```

Use `runic revision --autogenerate -m "..."` when `target_manifest` is set in
`env.py` — runic diffs the manifest against the live schema and emits candidate
`op.*` calls (always review before applying).

Use `runic check` in CI to gate deployments when the live schema diverges from
the manifest.

---

## Writing an explicit initial migration

If you prefer to skip `runic baseline` and write the initial migration by hand
(useful when the schema is small or well-understood), translate each OGM Field
declaration into the corresponding `op.*` call:

| OGM Field annotation | op.* call(s) needed |
| --- | --- |
| `Field(index=True)` | `op.create_range_index(label, prop)` |
| `Field(unique=True)` | `op.create_range_index(label, prop)` then `op.create_constraint("UNIQUE", "NODE", label, [prop])` |
| `Field(index_type="FULLTEXT")` | `op.create_fulltext_index(label, prop1, prop2, ...)` |
| `Field(index_type="VECTOR")` | `op.create_vector_index(label, prop, dimension, similarity)` |

See [example 06](../examples/06_baseline_generated.py) for a complete initial migration with comments.

---

## SchemaManager in production startup code

Some projects call `SchemaManager.sync_schema` on every app start as a
belt-and-braces check. This is fine for development or small graphs; avoid it
in large production graphs where every `CALL db.indexes()` scan adds latency:

```python
# app startup
from runic.migrate import SchemaManager
from myapp.db import adapter  # your configured adapter
from myapp.models import ALL_ENTITY_CLASSES

result = SchemaManager(adapter).validate_schema(ALL_ENTITY_CLASSES)
if not result.is_valid:
    raise RuntimeError(
        f"Schema out of sync — run 'runic upgrade head'. "
        f"Missing: {result.missing_indexes}"
    )
```

For production, prefer `runic check` in your CI/CD pipeline over runtime
validation.

---

## IndexManager vs SchemaManager — quick reference

```python
from runic.migrate import IndexManager, SchemaManager, create_adapter

adapter = create_adapter("falkordb", url="...", graph_name="...")

# IndexManager — single entity class at a time
mgr = IndexManager(adapter)
mgr.create_indexes(User)          # create all declared indexes; skip existing
mgr.ensure_indexes(Article)       # alias for create_indexes(if_not_exists=True)

# SchemaManager — multiple entity classes at once
schema = SchemaManager(adapter)
schema.sync_schema([User, Article, KnowsEdge])               # create missing
schema.sync_schema([User, Article, KnowsEdge], drop_extra=True)  # also drop extras
result = schema.validate_schema([User, Article, KnowsEdge])  # check only, no writes
print(schema.get_schema_diff([User, Article]))                # human-readable diff
```

Both accept a raw FalkorDB graph handle (auto-wrapped) for backward compat:

```python
import falkordb
db = falkordb.FalkorDB()
graph = db.select_graph("my_graph")
IndexManager(graph).create_indexes(User)
```
