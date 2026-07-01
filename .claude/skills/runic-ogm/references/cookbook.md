# runic.ogm Cookbook

Task-oriented recipes and gotchas. For the full API see
[api-reference.md](api-reference.md); for runnable code see
[../examples/](../examples/).

## Contents

- [runic.ogm Cookbook](#runicorm-cookbook)
  - [Contents](#contents)
  - [Session lifecycle](#session-lifecycle)
  - [Avoiding N+1](#avoiding-n1)
  - [Async patterns](#async-patterns)
  - [Polymorphism](#polymorphism)
  - [Custom repositories \& raw Cypher](#custom-repositories--raw-cypher)
  - [Pagination](#pagination)
  - [Fulltext \& vector search](#fulltext--vector-search)
  - [Multi-backend](#multi-backend)
  - [Testing](#testing)
  - [Gotchas](#gotchas)

---

## Session lifecycle

One session = one unit of work. Open it with a context manager so it always
closes; keep its scope short.

```python
with Session(driver) as session:
    session.add_all([a, b, c])
    session.commit()          # flush inserts/updates/deletes, clear tracking
```

- `add()`/`add_all()` stage inserts, `delete()` stages removals, attribute
  mutation on a loaded entity stages an update — all applied on `commit()`.
- `flush()` writes pending changes without ending the logical transaction;
  `commit()` flushes then clears tracking; `rollback()` discards pending state.
- The driver is reusable across many sessions — create it once, `close()` it on
  shutdown, not per request.

---

## Avoiding N+1

Lazy relationships fire one query per access. In a loop that's an N+1. Fetch
eagerly when you know you'll touch the relation:

```python
# BAD: one query for users + one per user for articles
for u in session.scalars(select(User)):
    print(len(u.articles))            # lazy load each iteration

# GOOD: a single query — but get() is per-entity, so for a *set* use a
# traversal query instead of eager get() in a loop:
rows = session.all_with_edges(
    select(User).alias("u")
    .traverse(User.articles, edge_alias="e").alias("a")
    .return_nodes("u", "a").return_edge("e")
)
```

`fetch=` on `get()` eager-loads one entity's relations in a single query; for
collections of parents, prefer one traversal query over many `get(..., fetch=)`
calls.

---

## Async patterns

```python
from runic.ogm import AsyncSession
from runic.ogm.driver.falkordb import AsyncFalkorDBDriver

driver = AsyncFalkorDBDriver(async_graph_handle)

async with AsyncSession(driver) as session:
    session.add(User(id="u1", name="Alice", email="a@x.io"))
    await session.commit()

    # Lazy access raises LazyLoadError in async — eager-fetch instead:
    user = await session.get(User, "u1", fetch=["articles"])
    for a in user.articles:           # already loaded, no await
        ...

    users = await session.scalars(select(User).where(User.active == True))
```

- `get`, `commit`, `flush`, `rollback`, `refresh`, `relate`, `unrelate`,
  `execute`, `scalars`, `scalar`, `count`, `all_rows`, `all_with_edges`, `close`
  are coroutines.
- Builders from `session.query()` / `fulltext_search()` / `vector_search()` are
  async — `await qb.all()`.
- Never rely on lazy loading; design every read with `fetch=` or a traversal.

---

## Polymorphism

Model a hierarchy with multi-label nodes sharing a `primary_label`. Querying a
base class returns concrete subtypes; querying a subtype filters to it.

```python
class Location(Node, labels=["Location"], primary_label="Location"):
    id: str
    title: str

class City(Location, labels=["Location", "City"], primary_label="Location"):
    population: int | None = None

class Country(Location, labels=["Location", "Country"], primary_label="Location"):
    iso_code: str

locs = Repository(session, Location).find_all()   # mix of City/Country instances
cities = session.scalars(select(City))            # only City
```

Subtypes inherit base fields. The decoder picks the concrete class from the node
labels.

---

## Custom repositories & raw Cypher

Subclass `Repository[T]` for domain queries. Prefer the builder; drop to Cypher
when the builder can't express it (edge-heavy reads, set operations, bulk
writes).

```python
class UserRepository(Repository[User]):
    def active_in_region(self, region: str) -> list[User]:
        return (self.query()
                .where((User.active == True) & (User.region == region))
                .order_by(User.name).all())

    def promote_all(self, region: str) -> None:
        self.cypher(
            "MATCH (u:User {region: $r}) SET u.tier = 'gold'",
            {"r": region}, write=True,
        )

    def author_counts(self):
        raw = self.cypher_raw(
            "MATCH (u:User) RETURN u.region AS region, count(u) AS n", {}
        )
        return [dict(zip(raw.columns, row)) for row in raw.rows]
```

- `cypher(q, params, returns=Cls)` maps rows to entities; `returns=int` maps a
  scalar; `write=True` for mutations.
- `cypher_one(...)` returns the first mapped row; `cypher_raw(...)` returns the
  unmapped `GraphResult` (`.columns`, `.rows`).
- Always parameterize (`$name`) — never string-format values into Cypher.

---

## Pagination

Offset-based via `skip`/`limit`. There is **no `Page` object**.

```python
repo = Repository(session, Article)
page = repo.find_all(skip=20, limit=10)          # third page of 10

# or with the builder, when you need filters/order:
page = session.scalars(
    select(Article).where(Article.status == "published")
    .order_by(Article.id).skip(20).limit(10)
)

total = repo.count()                              # for page math
```

Always `order_by` a stable key when paging so pages don't overlap or skip rows.

---

## Fulltext & vector search

FalkorDB-only, and the backing index must exist first. Declare the index on the
model, create it via `runic.migrate`'s `IndexManager`, then query.

```python
class Article(Node, labels=["Article"]):
    id: str = Field(primary_key=True)
    title: str = Field(index_type="FULLTEXT")
    body: str = Field(index_type="FULLTEXT")
    embedding: Vector | None = Field(index_type="VECTOR", default=None)

# Create indexes (needs the raw FalkorDB graph handle):
from runic.migrate import IndexManager
IndexManager(db.select_graph("app")).create_indexes(Article)

# Fulltext:
hits = (session.fulltext_search(Article, query="graph databases")
        .where(Article.published == True).limit(10).all())

# Vector KNN:
near = session.vector_search(
    Article, field=Article.embedding, vector=[0.1, 0.2, 0.3, 0.4], k=5
).where(Article.published == True).all()
```

Both return session-bound builders — chain `.where()`, `.order_by()`,
`.limit()`, then a terminal method. Use `.build()` to inspect the Cypher without
a live index.

---

## Multi-backend

Choose the backend at driver creation; the model and query code are unchanged.

| Capability | FalkorDB | Neo4j | Memgraph | ArcadeDB | Apache AGE |
|---|---|---|---|---|---|
| CRUD, traversal, aggregation | ✓ | ✓ | ✓ | ✓ | ✓ |
| `intern` / `Vector` / `GeoLocation` wrappers | ✓ | raw value | raw value | raw value | raw value |
| Fulltext search | ✓ | ✓¹ | ✓¹ | ✗ | ✗ |
| Vector KNN | ✓ | ✓¹ | ✓¹ | ✓¹ | ✗ |
| Native transactions | per-query | ✓ | ✓ | ✓ | ✓ |
| Multi-label nodes | ✓ | ✓ | ✓ | ✗ | ✗ |

¹ Requires pre-created named indexes and (Memgraph) MAGE modules.

Guidance: keep FalkorDB-specific features (native types, search) out of code
meant to be portable, or gate them on the backend. On AGE/ArcadeDB avoid
multi-label polymorphism. FalkorDB has no multi-statement transactions —
`commit()`/`rollback()` are in-memory bookkeeping there; each write is
individually atomic.

---

## Testing

Use embedded FalkorDB (redislite) for fast, serverless tests:

```python
from redislite import FalkorDB
from runic.ogm.driver.falkordb import FalkorDBDriver

def make_driver(name="test"):
    db = FalkorDB(protocol=2)              # protocol=2 avoids a redis-py 8 issue
    return FalkorDBDriver(db.select_graph(name))
```

The embedded backend does not support regex `=~` (`.matches()`) or
fulltext/vector indexes — those need a live FalkorDB v4+. Give each test a unique
graph name (or unique model `labels=`) to avoid metadata collisions across test
modules.

---

## Gotchas

- **Async + lazy = error.** `LazyLoadError`. Always `fetch=` in async.
- **Detached entity.** Lazy-accessing a relation after the session closed or you
  `expunge()`d raises `DetachedEntityError`. Fetch eagerly before detaching.
- **Edge-property filters need `optional=False`.** With `OPTIONAL MATCH`, a
  `WHERE` on the edge nullifies rows instead of dropping them, yielding `None`
  targets. Use a required traverse when filtering on edge properties.
- **Parenthesize boolean operands.** `A.x == 1 & A.y == 2` parses wrong; write
  `(A.x == 1) & (A.y == 2)`.
- **Constructors are keyword-only.** Positional args raise `TypeError`.
- **Indexes are declared, not created, by the ORM.** Creation belongs in
  `runic.migrate` migrations — see the `runic-migrate` skill.
- **`project()`/`aggregate()` don't return entities.** Read them with
  `all_rows()` (dicts), not `scalars()`.
- **Don't alias an aggregation column the same as the node alias.** The default
  node alias is `n` (or whatever you pass to `.alias()`). `count("*").as_("n")`
  collides with it and the decoder tries to read the integer as a node
  (`'int' object has no attribute 'labels'`). Name columns distinctly:
  `count("*").as_("total")`.
- **Group by a field, not the whole node.** To count/sum per field value, pass
  `group_by="alias.property"` (default alias `n`):
  `select(User).aggregate(count("*").as_("n_users"), group_by="n.city")` →
  `[{"n.city": "Berlin", "n_users": 3}, ...]`. A bare alias (`group_by="u"`)
  groups by the entire node — one row per node, which is rarely what you want
  for a per-field count.
- **Keep datetimes tz-aware.** The converter round-trips ISO-8601; naive
  datetimes lose their offset.
