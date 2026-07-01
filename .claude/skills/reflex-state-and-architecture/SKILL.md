---
name: reflex-state-and-architecture
description: >
  Reflex state design, event handlers, background tasks, form validation, page factory,
  service registry, repository pattern, database models, project architecture.
metadata:
  author: jens-rehpoehler
  version: "1.1"
  license: MIT
---

# Reflex Best Practices

This skill guides development in this Reflex.dev project. Read it before writing any new feature.

---

## 1. Project Architecture

Every feature lives in its own workspace package under `components/alloq-<name>/`. The main `app/` is the shell that assembles packages into a running application.

```
components/alloq-<feature>/
└── src/alloq_<feature>/
    ├── __init__.py          # public exports only
    ├── configuration.py     # Pydantic config schemas
    ├── backend/             # or backend.py — pure Python, no Reflex
    │   ├── models.py        # SQLModel table + UI models
    │   ├── repository.py    # async DB access
    │   └── services/        # business logic
    ├── state/               # or state.py — rx.State subclasses
    ├── components/          # or components.py — UI functions
    └── pages.py             # page factory functions

app/
├── app.py                   # assembles packages, creates rx.App
├── configuration.py         # root AppConfig + configure()
├── roles.py                 # Role definitions for RBAC
├── styles.py                # global style dicts + stylesheets
├── states/                  # app-level states (HomeState, etc.)
├── components/              # app-level reusable components
└── pages/                   # app-level pages
```

**Rule**: business logic belongs in `backend/`, reactive state in `state/`, UI in `components/`, routing in `pages.py`. Never mix concerns.

---

## 2. State Management

### Base class

All states inherit from `rx.State`. When you need the authenticated user, inherit from `UserSession` (from `appkit_user`):

```python
import reflex as rx
from appkit_user.authentication.states import UserSession

class MyFeatureState(rx.State):  # no auth needed
    ...

class MyFeatureState(UserSession):  # auth needed
    user = await self.authenticated_user
```

### State variable conventions

```python
class MyFeatureState(rx.State):
    # Data — typed, always with a default
    items: list[MyModel] = []
    selected_item: MyModel | None = None

    # Loading / UI flags
    is_loading: bool = False
    is_saving: bool = False

    # Filters / form fields
    search_query: str = ""
    selected_month: int = datetime.now(UTC).month

    # Private (not serialized to frontend) — prefix with _
    _initialized: bool = False

    # Browser-persisted — use rx.LocalStorage
    selected_tab: str = rx.LocalStorage("default", name="my-tab", sync=True)
```

### Computed vars

Use `@rx.var` for derived values. Avoid heavy computation — keep these O(n) at most.
Use `@rx.var(cache=True)` when the computation is more expensive or depends on a subset of state:

```python
@rx.var
def filtered_items(self) -> list[MyModel]:
    q = self.search_query.lower()
    return [i for i in self.items if q in i.name.lower()]

@rx.var
def total_count(self) -> int:
    return len(self.items)

@rx.var
def selected_year_str(self) -> str:
    # Bridge int → str for select components
    return str(self.selected_year)
```

Use async `@rx.var` only for DB queries that must stay reactive:

```python
@rx.var
async def chart_data(self) -> list[dict]:
    user = await self.authenticated_user
    async with rx.asession() as session:
        ...
```

### Event handlers

**→ See [`examples/state_example.py`](examples/state_example.py) for full annotated examples.**

```python
# Sync handler
@rx.event
def set_filter(self, value: str) -> None:
    self.search_query = value

# Async handler — yield after each mutation to push state to frontend
@rx.event
async def load_data(self) -> AsyncGenerator:
    self.is_loading = True
    yield
    try:
        self.items = await my_repo.get_all()
    except Exception:
        logger.exception("Failed to load")
        yield rx.toast.error("Laden fehlgeschlagen", position="top-right")
    finally:
        self.is_loading = False

# Chaining: iterate over another handler
async for _ in self.load_data():
    yield

# Background task — state mutations inside `async with self:`
@rx.event(background=True)
async def export_data(self) -> AsyncGenerator:
    async with self:
        self.is_exporting = True
    yield
    # ... heavy work ...
    async with self:
        self.is_exporting = False
    yield rx.toast.success("Fertig", position="top-right")

# Background task invocation — always yield the method reference
yield MyState.export_data
```

### Page on_load pattern

```python
@rx.event
async def on_load(self) -> AsyncGenerator:
    """Called via on_load=[MyState.on_load] in the page factory."""
    async for _ in self.load_data():
        yield
```

### Cache invalidation

```python
def _clear_caches(self) -> None:
    self.items.clear()
    self.expanded_rows.clear()
    self.detail_cache.clear()
```

---

## 3. UI Components — appkit_mantine

### Documentation rule

**Before using any `mn.*` or `rx.*` component not shown in [`examples/components_example.py`](examples/components_example.py), look up its API in the official documentation via the Context7 MCP server:**

```
# For appkit_mantine / Mantine components:
resolve-library-id("mantine")  → then get-library-docs(id, topic="<component name>")

# For Reflex-specific components and primitives:
resolve-library-id("reflex")   → then get-library-docs(id, topic="<component name>")
```

Additional real-world usage examples are available in the appkit repository:
**https://github.com/jenreh/appkit/tree/main/app/pages/examples**

| File | Components covered |
|---|---|
| `button_examples.py` | `mn.button`, `mn.action_icon`, `mn.action_icon.group` |
| `input_examples.py` | `mn.text_input`, `mn.textarea`, `mn.number_input`, `mn.tags_input`, `mn.password_input`, `mn.json_input`, `mn.slider`, `mn.range_slider`, `mn.switch` |
| `date_examples.py` | `mn.date_input`, `mn.date_picker_input`, `mn.date_time_picker`, `mn.month_picker_input`, `mn.time_input`, `mn.calendar` |
| `modal_examples.py` | `mn.modal`, `mn.modal.root`, `mn.modal.stack` |
| `overlay_examples.py` | `mn.tooltip`, `mn.hover_card` |
| `table_examples.py` | `mn.table`, `mn.table.thead/tbody/tr/th/td`, `sticky_header`, `with_table_border` |
| `charts_examples.py` | `mn.bar_chart`, `mn.line_chart`, `mn.area_chart` |
| `data_display_examples.py` | `mn.badge`, `mn.avatar`, `mn.card`, `mn.progress` |
| `navigation_examples.py` | `mn.tabs`, `mn.nav_link`, `mn.breadcrumbs` |
| `feedback_examples.py` | `mn.alert`, `mn.notification`, `mn.loader` |
| `combobox_examples.py` | `mn.select`, `mn.multi_select`, `mn.combobox` |

Always check the docs for:
- Correct prop names (e.g. `left_section` not `leftSection`, `with_border` not `withBorder`)
- Event handler signatures (`on_change`, `on_blur`, `on_visibility_change`)
- Controlled (`value=` + `on_change=`) vs uncontrolled (`default_value=` + `on_blur=`) usage

**→ For all component API, usage patterns, and visual guidelines, use the `appkit-mantine-reference` skill.**

---

## 4. Component Functions

**→ See [`examples/components_example.py`](examples/components_example.py) for full annotated examples.**

### Always functions, never classes

Component functions accept state vars as arguments for reactivity:

```python
def my_card(title: str, value: rx.Var | str) -> rx.Component:
    return mn.card(mn.heading(value, size="6", fw="bold"), ...)

# Correct — reactive binding
my_card(title="Users", value=MyState.user_count)
# Wrong — static, won't update
my_card(title="Users", value=42)
```

### Composition hierarchy

Build small → compose big. Prefix private helpers with `_`:

```python
def _filter_bar() -> rx.Component: ...
def _data_table() -> rx.Component: ...
def _empty_state() -> rx.Component: ...

def my_page_content() -> rx.Component:
    return mn.stack(
        _filter_bar(),
        rx.cond(MyState.is_loading, mn.loader(),
            rx.cond(MyState.items, _data_table(), _empty_state())),
        gap="md", w="100%",
    )
```

Use `rx.cond` and `rx.foreach` for conditionals and iteration — never bare Python `if` inside component functions.

---

## 5. Page Factory Pattern

**→ See [`examples/pages_example.py`](examples/pages_example.py) for the full annotated example including multi-page factories and registration.**

Every feature package exports a factory function (not a bare page):

```python
# pages.py
from appkit_user.authentication.templates import authenticated

def create_my_feature_page(navbar: rx.Component, route: str = "/my-feature", title: str = "My Feature") -> Callable:
    @authenticated(route=route, title=title, navbar=navbar, on_load=MyFeatureState.on_load, admin_only=True)
    def my_feature_page() -> rx.Component:
        return rx.flex(header(title), my_page_content(), direction="column", gap="4", w="100%", p="2rem")
    return my_feature_page

# Register in app/app.py:
create_my_feature_page(app_navbar())
```

---

## 6. Service Registry & Dependency Injection

Use `service_registry()` (from `appkit_commons`) as the single IoC container.

### Configuration

```python
# configuration.py
from appkit_commons.registry import service_registry

class MyFeatureConfig(BaseConfig):
    api_url: str | None = None
    api_key: SecretStr | None = None
```

Register in `configure()` in `app/configuration.py` by adding to `AppConfig`:

```python
class AppConfig(ApplicationConfig):
    my_feature: MyFeatureConfig | None = None
```

### Services

```python
class MyService:
    def __init__(self) -> None:
        self._config = service_registry().get(MyFeatureConfig)
```

Register in `app/app.py` `_initialize_services()` in dependency order.

### Accessing in state

```python
def _do_work(self) -> None:
    config = service_registry().get(MyFeatureConfig)
    svc = service_registry().get(MyService)
```

---

## 7. Repository Pattern

`BaseRepository` (from `appkit_commons`) already provides full CRUD:
`create()`, `update()`, `save()`, `find_by_id()`, `find_all()`, `delete_by_id()`, `delete()`, `exists_by_id()`, `count()`

Only add custom methods for queries not covered by the base class (e.g., `find_by_email`, `find_all_paginated`):

```python
# backend/repository.py

from appkit_commons.repositories.base import BaseRepository
from appkit_commons.database.session import get_asyncdb_session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

class MyModelRepository(BaseRepository[MyModelEntity]):

    async def find_by_name(
        self, session: AsyncSession, name: str
    ) -> MyModelEntity | None:
        result = await session.execute(
            select(MyModelEntity).where(MyModelEntity.name == name)
        )
        return result.scalar_one_or_none()


my_model_repo = MyModelRepository(MyModelEntity)
```

Always use `get_asyncdb_session()` — not `rx.asession()` — as the session factory:

```python
# In state event handlers
async with get_asyncdb_session() as session:
    items = await my_model_repo.find_all(session)
    entity = await my_model_repo.find_by_id(session, item_id)
    await my_model_repo.create(session, new_entity)
    await my_model_repo.update(session, entity)
    await my_model_repo.delete_by_id(session, item_id)
```

Never use `rx.asession()` — it does not work in background processors or callbacks outside the Reflex request lifecycle.

---

## 8. Database Models

### SQLAlchemy Entity (DB table)

Inherit from both `Entity` and `Base` from `appkit_commons.database.entities`. `Entity` provides `id`, `created`, and `updated` automatically. Add `to_dict()` for conversion to Pydantic/display models:

```python
# backend/entities.py
from appkit_commons.database.entities import Base, Entity
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

class MyEntity(Entity, Base):
    __tablename__ = "my_feature_items"

    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(default=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active,
        }
```

### Pydantic display model (UI-layer DTO)

Use `rx.Base` for models stored in Reflex state — never store SQLAlchemy `table=True` models directly:

```python
# backend/models.py
import reflex as rx

class MyModel(rx.Base):
    """UI-only DTO — safe to store in state."""
    id: int
    name: str
    is_active: bool = True
```

Convert in state: `self.items = [MyModel(**e.to_dict()) for e in entities]`

**Important**: Never store SQLAlchemy entity objects (those with relationships) directly in Reflex state — lazy-loaded relationships will fail outside the session context.

---

## 9. Roles & Authorization

Define new roles in `app/roles.py`:

```python
MY_FEATURE_ROLE = Role(name="my-feature", label="My Feature", group=MY_GROUP)
ALL_ROLES = [..., MY_FEATURE_ROLE]
```

Use in page factory: `admin_only=True` or `role=MY_FEATURE_ROLE.name`.

Use in navbar:

```python
requires_role(
    sidebar_item(label="My Feature", icon="star", url="/my-feature"),
    role=MY_FEATURE_ROLE.name,
)
```

---

## 10. Anti-Patterns

| Anti-pattern | Correct approach |
|---|---|
| Storing SQLAlchemy entity objects in state | Use `rx.Base` display models |
| Calling `service_registry()` at module level | Call inside functions/methods |
| Mutating state without `yield` in async gen | Always `yield` after mutations |
| Fat page functions | Decompose into `_section()` helpers |
| Logic in components | Move to state event handlers or `@rx.var` |
| `rx.asession()` in background tasks / callbacks | Use `get_asyncdb_session()` |
| `and` / `or` inside `rx.cond(...)` | Use `&` and `\|` operators |
| Calling a background task directly from a handler | `yield MyState.background_task` — always yield the method reference |
| Duplicating CRUD in repositories | Use `BaseRepository` methods directly; only add custom query methods |

---

## 11. File & Naming Conventions

```
state/my_feature_state.py        → MyFeatureState(rx.State)
components/my_feature_table.py   → my_feature_table() → rx.Component
components/my_feature_dialogs.py → create_dialog(), delete_dialog()
backend/models.py                → MyModel, MyModelDisplay
backend/repository.py            → MyModelRepository (static methods)
pages.py                         → create_my_feature_page(navbar)
configuration.py                 → MyFeatureConfig(BaseConfig)
```

---

## 12. Form Validation Pattern

Use a **dedicated `rx.State` subclass** (not mixed into the main feature state) to hold form field values, per-field error strings, and validation logic. This keeps form concerns isolated and testable.

**→ See [`examples/form_validation_example.py`](examples/form_validation_example.py) for the full annotated example.**

### Key rules

- Store each field as `str` — inputs are always strings; parse/validate explicitly.
- Store per-field error as `str` — empty string means no error.
- Decorate `validate_*` methods with `@rx.event` so the UI can bind them to `on_blur`.
- Expose `@rx.var` `is_form_valid` / `is_form_invalid` — bind to the submit button's `disabled` prop.
- `form_version: int` counter — increment in `initialize()` to force re-render of controlled inputs on reset.
- Async DB uniqueness checks (`validate_email_unique`) — attach to `on_blur`, **not** `on_change` (avoids a DB hit on every keystroke).
- Call `initialize()` from the parent state's `open_add_modal` / `open_edit_modal`, returning `[ValidationState.initialize(...)]`.
- Call `validate_all()` at the top of the submit handler to surface all errors before bailing out.

### Pattern summary

```python
class ItemValidationState(rx.State):
    form_version: int = 0       # increment on initialize() to reset controlled inputs
    name: str = ""              # one field var per input
    name_error: str = ""        # one error var per field (empty = no error)

    @rx.event
    def initialize(self, item: Item | None = None) -> None:
        # populate or reset all fields; clear all errors; form_version += 1
        ...

    def set_name(self, value: str) -> None:   # setter: update field + validate inline
        self.name = value
        self.validate_name()

    @rx.event
    def validate_name(self) -> None: ...      # sync validator → on_blur or on_change
    @rx.event
    async def validate_email_unique(self) -> None: ...  # async DB check → on_blur only
    @rx.event
    def validate_all(self) -> None: ...       # call before submit

    @rx.var
    def is_form_valid(self) -> bool: ...
    @rx.var
    def is_form_invalid(self) -> bool: return not self.is_form_valid

# Parent state opens modal and initialises the form in one call:
def open_add_modal(self) -> list[rx.event.EventSpec]:
    self.is_add_modal_open = True
    return [ItemValidationState.initialize()]

# Submit guard:
async def submit_item(self) -> AsyncGenerator:
    form_state = await self.get_state(ItemValidationState)
    if form_state.is_form_invalid:
        yield ItemValidationState.validate_all()
        return
    # use form_state.name, form_state.email, etc.
```

---

## 13. Example Files

See the `examples/` folder alongside this SKILL.md:

| File | Demonstrates |
|---|---|
| `state_example.py` | Full state class — loading, computed vars, pagination |
| `components_example.py` | appkit_mantine component patterns — cards, table, chart |
| `pages_example.py` | Page factory with auth, on_load, navbar |
| `background_task_example.py` | File upload + async background processing |
| `form_validation_example.py` | Isolated validation state — fields, errors, on_blur uniqueness check, submit guard |

---

**→ For component API, usage patterns, color reference, and visual guidelines, use the `appkit-mantine-reference` skill.**
