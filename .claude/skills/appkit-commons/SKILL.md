---
name: appkit-commons
description: >
  appkit-commons usage patterns: configuration (YAML profiles, env overrides, secrets),
  service registry, repository pattern, database entities, custom column types
  (EncryptedString, ArrayType), and scheduler (APScheduler, PGQueuer). Apply automatically
  when adding new features, services, repositories, scheduled tasks, or configuring
  the application stack.
metadata:
  author: jens-rehpoehler
  version: "2.0"
  license: MIT
---

# appkit-commons Best Practices

Read before writing any new feature. Covers configuration, DI, persistence, and scheduling.

---

## 1. Configuration

### App initialization pattern

Define a cached `configure()` function in `config.py`. Call it from `__init__.py` before anything else.

```python
# config.py
from functools import lru_cache
from appkit_commons.configuration import BaseConfig
from appkit_commons.configuration.configuration import Configuration, Environment
from appkit_commons.registry import service_registry


class MyFeatureConfig(BaseConfig):
    api_url: str | None = None
    api_key: str = ""


class ApplicationConfig(BaseConfig):
    version: str
    name: str
    logging: str
    environment: Environment | None = Environment.local
    my_feature: MyFeatureConfig = MyFeatureConfig()


@lru_cache(maxsize=1)
def configure() -> Configuration[ApplicationConfig]:
    return service_registry().configure(ApplicationConfig, env_file=".env")
```

```python
# __init__.py
import logging
from dotenv import load_dotenv
from myapp.config import configure
from appkit_commons.configuration.logging import init_logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

load_dotenv(override=True)
configuration = configure()
init_logging(configuration)
```

`service_registry().configure()` auto-registers every nested config object by its own type —
`ApplicationConfig`, `MyFeatureConfig`, `DatabaseConfig`, `ServerConfig`, etc. are all retrievable after this call.

### Accessing config anywhere

Use `service_registry().get()` with the exact config class. Always call inside functions/methods, never at module level.

```python
from appkit_commons.registry import service_registry
from myapp.config import ApplicationConfig, LlmConfig, MyFeatureConfig

# top-level app config
cfg = service_registry().get(ApplicationConfig)
log.info("Starting %s v%s", cfg.name, cfg.version)

# nested sub-config — registered automatically by configure()
llm_cfg = service_registry().get(LlmConfig)
feature_cfg = service_registry().get(MyFeatureConfig)
```

### YAML + profiles

`BaseConfig` loads from `config.yaml` first, then merges `config.<profile>.yaml`.

```yaml
# config.yaml
app:
  name: my-app
  version: "1.0"
  logging: configuration/logging.yaml
  database:
    host: localhost
    name: mydb
```

```yaml
# config.development.yaml
app:
  database:
    echo: true
```

Set active profile via `PROFILE=development` env var. Multiple profiles merge in order.

### Environment overrides

`__` as nested delimiter maps to config hierarchy:

```bash
APP__DATABASE__HOST=prod-db.internal
APP__MY_FEATURE__API_KEY=secret123
```

### Secret values

Prefix with `secret:` to resolve at runtime via Azure Key Vault or local env:

```yaml
app:
  my_feature:
    api_key: "secret:MY_FEATURE_API_KEY"
```

`get_secret("MY_FEATURE_API_KEY")` tries `SECRET_PROVIDER` env var (AZURE or LOCAL).

### DatabaseConfig fields

```python
# Key fields with defaults
host: str = "localhost"
port: int = 5432
name: str = "postgres"
username: str = "postgres"
password: SecretStr = SecretStr("postgres")
encryption_key: SecretStr = SecretStr("")   # required for EncryptedString columns
pool_size: int = 10
max_overflow: int = 30
echo: bool = False
ssl_mode: str = "disable"
url_override: str | None = None             # override full URL
```

---

## 2. Service Registry

Single IoC container. All services registered as singletons by type.

```python
from appkit_commons import service_registry

# Register (in app startup / _initialize_services, in dependency order)
registry = service_registry()
registry.register(MyService())
registry.register_as(MyProtocol, my_impl)   # register under a different type

# Retrieve (anywhere)
svc = service_registry().get(MyService)
config = service_registry().get(MyFeatureConfig)

# Introspect
registry.has(MyService)           # bool
registry.list_registered()        # list[type]
registry.unregister(MyService)
```

Call `service_registry()` inside functions/methods — never at module level.

### Service pattern

```python
class MyService:
    def __init__(self) -> None:
        self._config = service_registry().get(MyFeatureConfig)

    async def do_work(self) -> str:
        ...
```

---

## 3. Repository Pattern

`BaseRepository[T]` provides full async CRUD. Add custom methods only for queries not in the base.

### Define

```python
from appkit_commons.database.base_repository import BaseRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class MyEntityRepository(BaseRepository[MyEntity]):

    @property
    def model_class(self) -> type[MyEntity]:
        return MyEntity

    async def find_by_name(
        self, session: AsyncSession, name: str
    ) -> MyEntity | None:
        result = await session.execute(
            select(MyEntity).where(MyEntity.name == name)
        )
        return result.scalar_one_or_none()


my_entity_repo = MyEntityRepository()
```

### Full CRUD reference

```python
from appkit_commons.database.session import get_asyncdb_session

async with get_asyncdb_session() as session:
    # Create
    entity = await my_entity_repo.create(session, MyEntity(name="foo"))

    # Read
    item  = await my_entity_repo.find_by_id(session, item_id)
    items = await my_entity_repo.find_all(session)
    batch = await my_entity_repo.find_all_by_ids(session, [1, 2, 3])
    exists = await my_entity_repo.exists_by_id(session, item_id)
    total  = await my_entity_repo.count(session)

    # Update
    entity.name = "bar"
    await my_entity_repo.update(session, entity)

    # Save (create or update based on id)
    entity = await my_entity_repo.save(session, entity)
    saved  = await my_entity_repo.save_all(session, [e1, e2])

    # Delete
    await my_entity_repo.delete_by_id(session, item_id)
    await my_entity_repo.delete(session, entity)
    count = await my_entity_repo.delete_all_by_ids(session, [1, 2])
    count = await my_entity_repo.delete_all(session)
```

The session auto-commits on exit and rolls back on exception — do not call `session.commit()` manually.

Never use `rx.asession()` — it breaks in background tasks and callbacks outside the Reflex request lifecycle.

---

## 4. Database Entities

### Entity + Base

```python
from appkit_commons.database.entities import Base, Entity
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class MyEntity(Entity, Base):
    __tablename__ = "my_items"

    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "is_active": self.is_active}
```

`Entity` mixin auto-provides:

- `id: int` — PK, auto-increment, indexed
- `created: datetime` — UTC, set on insert via `server_default`
- `updated: datetime` — UTC, auto-updated on each change

### Custom column types

```python
from appkit_commons.database.entities import EncryptedString, ArrayType

class MyEntity(Entity, Base):
    __tablename__ = "my_items"

    secret_field: Mapped[str] = mapped_column(EncryptedString)   # Fernet-encrypted at rest
    tags: Mapped[list] = mapped_column(ArrayType)                 # native ARRAY (PG) / JSON (SQLite)
```

`EncryptedString` reads cipher key from `DatabaseConfig.encryption_key` at runtime via service registry.
`ArrayType` is dialect-agnostic — no migration changes needed between PG and SQLite.

### Pydantic display model (state-safe DTO)

Never store SQLAlchemy entities in Reflex state — lazy-loaded relationships fail outside the session.

```python
from pydantic import BaseModel

class MyModel(BaseModel):
    id: int
    name: str
    is_active: bool = True

# In event handler:
self.items = [MyModel(**e.to_dict()) for e in entities]
```

---

## 5. Alembic Migrations

Never use `--autogenerate`. Write migrations manually.

`down_revision` must be the `revision` string from the previous migration file, not the filename:

```python
# ✅ CORRECT — open the previous migration file and copy its `revision` value
revision = "3f7a2d019e5b"
down_revision = "8a6c1e2b9f04"

# ❌ WRONG — filename is not the revision ID
down_revision = "2026_05_05_add_items_table"
```

The `# Revises:` comment in the module docstring must match `down_revision`.

---

## 6. Scheduler

Two backends: `APScheduler` (distributed-safe, default) and `PGQueuerScheduler`.

### Define a scheduled service

```python
from appkit_commons.scheduler import ScheduledService, CronTrigger, IntervalTrigger
from appkit_commons.database.session import get_asyncdb_session


class NightlyCleanupService(ScheduledService):
    job_id = "nightly_cleanup"
    name = "Nightly Cleanup"

    @property
    def trigger(self) -> CronTrigger:
        return CronTrigger(hour=2, minute=0)

    async def execute(self, *args, **kwargs) -> None:
        async with get_asyncdb_session() as session:
            await my_entity_repo.delete_old_items(session)
```

### Trigger types

```python
# Cron — standard cron fields, all optional (default *)
CronTrigger(hour=2, minute=30)               # daily at 02:30
CronTrigger(day_of_week="mon", hour=9)       # every Monday 09:00
CronTrigger(minute="*/15")                   # every 15 minutes

# Fixed interval
IntervalTrigger(minutes=5)                   # every 5 minutes
IntervalTrigger(hours=1, minutes=30)         # every 90 minutes

# Calendar interval (month/year-aware)
from appkit_commons.scheduler import CalendarIntervalTrigger
CalendarIntervalTrigger(months=1, day=1)     # 1st of each month
```

### Register and start

```python
from appkit_commons.scheduler import APScheduler

scheduler = APScheduler()
scheduler.add_service(NightlyCleanupService())
service_registry().register(scheduler)

# In app lifespan:
await scheduler.start()

# On shutdown:
await scheduler.shutdown()
```

`APScheduler` auto-configures from `DatabaseConfig`. In multi-node deployments it coordinates via the SQL datastore so each job runs on only one node. Uses `PsycopgEventBroker` for real-time scheduling when PostgreSQL is available.

---

## 7. Anti-Patterns

| Anti-pattern | Correct approach |
| --- | --- |
| `rx.asession()` in background tasks / callbacks | `get_asyncdb_session()` |
| `service_registry()` at module level | Call inside functions/methods |
| SQLAlchemy entities in Reflex state | Convert to Pydantic `BaseModel` via `to_dict()` |
| Duplicating CRUD in repos | Use `BaseRepository` built-ins; add only custom query methods |
| `--autogenerate` for Alembic | Write migrations manually |
| Hardcoded credentials in YAML | Use `secret:` prefix, resolve via `get_secret()` |
| `session.commit()` inside `get_asyncdb_session()` block | Session auto-commits on context exit |
