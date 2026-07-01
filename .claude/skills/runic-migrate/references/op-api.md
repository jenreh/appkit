# GraphOperations (`op`) — Full API Reference

The `op` argument injected into every `upgrade(op)` and `downgrade(op)` function
is a `runic.migrate.operations.GraphOperations` instance. In `--preview` mode it logs
the intended operation instead of executing it.

---

## Index operations

### Range index

```python
op.create_range_index(label: str, prop: str, *, rel: bool = False) -> None
op.drop_range_index(label: str, prop: str, *, rel: bool = False) -> None
```

`rel=True` creates/drops a range index on a relationship type instead of a node label.

```python
op.create_range_index("User", "email")
op.create_range_index("FOLLOWS", "since", rel=True)
op.drop_range_index("User", "email")
op.drop_range_index("FOLLOWS", "since", rel=True)
```

### Full-text index

```python
op.create_fulltext_index(
    label: str,
    *props: str,
    language: str | None = None,
    stopwords: list[str] | None = None,
) -> None
op.drop_fulltext_index(label: str, *props: str) -> None
```

```python
op.create_fulltext_index("Post", "title", "body")
op.create_fulltext_index("Article", "title", language="german",
                          stopwords=["der", "die", "das"])
op.drop_fulltext_index("Post", "title", "body")
```

### Vector index (HNSW)

```python
op.create_vector_index(
    label: str,
    prop: str,
    dimension: int,
    similarity: str,           # "cosine" | "euclidean"
    *,
    m: int = 16,
    ef_construction: int = 200,
    ef_runtime: int = 10,
) -> None
op.drop_vector_index(label: str, prop: str) -> None
```

```python
op.create_vector_index("Product", "embedding", 256, "cosine")
op.create_vector_index("Doc", "vec", 128, "euclidean",
                        m=32, ef_construction=400, ef_runtime=20)
op.drop_vector_index("Product", "embedding")
```

---

## Constraint operations

```python
op.create_constraint(
    kind: str,     # "UNIQUE" | "MANDATORY"
    entity: str,   # "NODE"   | "RELATIONSHIP"
    label: str,
    props: list[str],
) -> None
op.drop_constraint(kind: str, entity: str, label: str, props: list[str]) -> None
```

`create_constraint("UNIQUE", ...)` automatically creates the required backing
range index if it does not exist, then polls `CALL db.constraints()` until
status reaches `OPERATIONAL`. Raises `ConstraintFailedError` on `FAILED`.

```python
op.create_constraint("UNIQUE",    "NODE",         "User",    ["email"])
op.create_constraint("MANDATORY", "NODE",         "User",    ["email"])
op.create_constraint("UNIQUE",    "RELATIONSHIP", "FOLLOWS", ["id"])
op.drop_constraint("UNIQUE",    "NODE",         "User",    ["email"])
op.drop_constraint("MANDATORY", "NODE",         "User",    ["email"])
```

**Ordering rule:** in `downgrade`, always drop constraints *before* the backing
range index, or FalkorDB will refuse the index drop.

---

## Data transformation operations

All data-transform ops are **batched and idempotent** — safe to re-run after a
partial failure.

### rename_property

```python
op.rename_property(label: str, old: str, new: str, batch: int = 10_000) -> None
```

Iterates pages of `MATCH (n:label) WHERE n.old IS NOT NULL AND n.new IS NULL`
until exhausted.

```python
op.rename_property("User", "fname", "first_name")
op.rename_property("Order", "ts", "created_at", batch=5_000)
```

### relabel_nodes

```python
op.relabel_nodes(old: str, new: str, batch: int = 10_000) -> None
```

**Note:** requires multi-label Cypher support (`SET n:New REMOVE n:Old`). Raises
`NotImplementedError` on Apache AGE and ArcadeDB, which do not allow assigning
multiple labels to a single vertex.

```python
op.relabel_nodes("Member", "User")
```

### seed

```python
op.seed(merge_query: str, rows: list[dict]) -> None
```

Executes `UNWIND $rows AS row <merge_query>` — idempotent reference data load.

```python
op.seed(
    "MERGE (r:Role {name: row.name}) SET r.system = row.system",
    [{"name": "admin", "system": True}, {"name": "user", "system": False}],
)
```

### run_cypher

```python
op.run_cypher(query: str, params: dict | None = None) -> Any
```

Raw escape hatch for anything not covered by the higher-level ops.

```python
op.run_cypher(
    "MATCH (u:User) WHERE u.active IS NULL SET u.active = true"
)
op.run_cypher(
    "CREATE (c:Config {key: $k, value: $v})",
    {"k": "schema_version", "v": "2"},
)
```

---

## SchemaManifest (for autogenerate / check)

Set `target_manifest` in `env.py`; runic diffs it against the live schema.

```python
from runic.migrate.manifest import (
    SchemaManifest,
    RangeIndex,
    FulltextIndex,
    VectorIndex,
    UniqueConstraint,
    MandatoryConstraint,
)

manifest = SchemaManifest(
    range_indexes=[
        RangeIndex("User", "email"),
        RangeIndex("User", "created_at"),
        RangeIndex("FOLLOWS", "since", rel=True),
    ],
    fulltext_indexes=[
        FulltextIndex("Post", ["title", "body"], language="english"),
    ],
    vector_indexes=[
        VectorIndex("Product", "embedding", dimension=256, similarity="cosine"),
    ],
    constraints=[
        UniqueConstraint("NODE", "User", ["email"]),
        MandatoryConstraint("NODE", "User", ["email"]),
    ],
)
```

**Autogenerate limitations:**

- Covers indexes and constraints only — node/relationship "schema" is implicit.
- Cannot detect renames (generates drop + create). Always review before applying.
- Cannot generate data migrations.
- Generated bodies are marked `# AUTOGENERATED — review before applying`.

---

## IndexManager and SchemaManager (OGM-driven index creation)

`IndexManager` and `SchemaManager` read index declarations from **OGM model
Field annotations** (`Field(index=True)`, `Field(unique=True)`,
`Field(index_type='FULLTEXT')`, `Field(index_type='VECTOR')`) and issue the
corresponding adapter DDL calls. They complement migration scripts: use them
for initial development / CI bootstrapping, and write explicit `op.*` migration
scripts for version-controlled production schema changes.

```python
from runic.migrate import IndexManager, SchemaManager, create_adapter

adapter = create_adapter(
    "falkordb",
    url="falkor://localhost:6379",
    graph_name="my_graph",
)
```

### IndexManager

Creates indexes and constraints for a single entity class.

```python
manager = IndexManager(adapter)

# Create all indexes declared on User (range, unique, fulltext, vector)
manager.create_indexes(User)

# Same, but skip specs that already exist (default behaviour)
manager.ensure_indexes(Article)
```

`create_indexes(entity_class, *, if_not_exists=True)` batches fulltext specs
for the same label into a single `create_fulltext_index(label, *props)` call
(required by Neo4j / Memgraph).

Also accepts a **raw FalkorDB graph handle** (auto-wrapped) for backward compat:

```python
import falkordb
db = falkordb.FalkorDB()
graph = db.select_graph("my_graph")
IndexManager(graph).create_indexes(User)
```

### SchemaManager

Validates and syncs indexes across **multiple** entity classes at once.

```python
schema = SchemaManager(adapter)

# Check which declared indexes are missing or extra in the live graph
result = schema.validate_schema([User, Article, KnowsEdge])
# result.is_valid, result.missing_indexes, result.extra_indexes, result.errors

# Create missing indexes; optionally drop indexes not declared on any entity
schema.sync_schema([User, Article, KnowsEdge])
schema.sync_schema([User, Article, KnowsEdge], drop_extra=True)

# Human-readable diff for logging / CI output
print(schema.get_schema_diff([User, Article]))

# Structured snapshot for programmatic inspection
info = schema.get_schema_info([User, Article])
# info.is_valid, info.declared_count, info.existing_count,
# info.missing_count, info.extra_count, info.missing, info.extra

# ArcadeDB: ensure CREATE VERTEX TYPE / CREATE EDGE TYPE DDL (no-op elsewhere)
schema.ensure_entity_types([User, Article, KnowsEdge])
```

**When to use `IndexManager` vs migration scripts:**

| Situation | Use |
| --- | --- |
| Development / CI bootstrap | `SchemaManager.sync_schema([...])` |
| Production schema change | `op.*` migration script in `versions/` |
| CI gate (schema in sync?) | `SchemaManager.validate_schema([...])` or `runic check` |
| Single entity type setup | `IndexManager.create_indexes(Model)` |
