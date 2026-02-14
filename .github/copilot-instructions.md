---
applyTo: "**"
description: "Main Copilot instructions for the appkit project - Reflex-Mantine component library with comprehensive development workflow and architecture guidelines"
---

# Reflex-Mantine Component Library

**A comprehensive Reflex wrapper library for Mantine UI components with production-ready examples.**

> **Purpose:** Guide GitHub Copilot & Copilot Chat to align suggestions with our tech stack, workflows, and quality bars.
> **Stacks:** Python 3.13 · Reflex (UI) · FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic · FastMCP · LangChain

---

## 1) Golden Rules (Short, Actionable)
1. **Think → Memory → Tools → Code → Memory.** Start with step-by-step reasoning (using the tool code-reasoning); **search Memory first**; pick tools; code minimal diff; **write learnings back to Memory**.
2. **Tests are truth.** On failures: **fix code first**. Change tests only if they clearly diverge from spec.
3. **Small, safe changes.** Prefer smallest viable diff; add tests for new behavior **before** code.
4. **Consistency > cleverness.** Follow this file’s SOPs and stack idioms.
5. **Memory multiplies.** Persist decisions, patterns, error signatures, and proven fixes.
6. Do NOT generate extensive documentation, summaries or comments unless explicitly requested.
7. Do NOT use --autogenerate for new Alembic migrations; write them manually.
8. Do NOT use "cat" to create new files; ALWAYS use the available tools!

> Rule of thumb: prefer *local* changes over cross-module refactors.

---

## 2) Task Bootstrap Pattern (for Inline Copilot & Chat)
Paste/edit this at the top of the change (as a comment) to steer Copilot:

```markdown
<!-- plan:start
goal: <one line clear goal>
constraints:
- Python 3.13; Reflex UI; FastAPI; SQLAlchemy 2.0; Alembic; Pydantic
- logging: no f-strings in logger calls
- minimal diff; add/adjust tests first
definition_of_done:
- tests pass; coverage ≥ 80%; lint/type checks clean; memory updated
steps:
1) Search Memory for "<keywords>"
2) Draft/adjust failing test to capture expected behavior
3) Implement minimal code change
4) Run make test; iterate until green
5) Update Memory: decisions, patterns, error→fix
plan:end -->
```

---

## 3) Tooling Decision Matrix (Condensed)

| Situation | Primary | Secondary | Store to Memory |
|---|---|---|---|
| API/pattern uncertainty | **Context7** | — | Canonical snippet + link; edge cases |
| Ecosystem bug/issue | **DuckDuckGo** | — | Minimal repro; versions; workaround |
| Repeated test failure | **Memory (search)** | Context7 | Error signature → fix; root cause |
| New feature scaffold | **Context7** | — | How‑to snippet; checklist |
| House style/tooling | **This file** | Context7 | Checklist results |

**Prefer official docs; widen via web search when cross-version issues arise.**

---

## 4) SOP — Development Workflow

### Prepare
1. **Memory first:** search for prior solutions and patterns.
2. **Reasoning plan:** use the *Task Bootstrap Pattern*.
3. **Sync tools:** `make install` (uses **uv**, Python 3.13).
4. **Baseline:** `make test` to snapshot current failures.

### Triage Failures
- Read the **first** failing assertion; map to spec.
- If tests match spec → fix code. If tests diverge → document and adjust spec/tests (after approval).
- Add/adjust unit tests to codify expected behavior.

### Implement (Minimal Diff)
- Tests-first for new behavior.
- Use only approved stacks. Examples:
  - **Logging (no f-strings):**
    ```python
    import logging
    log = logging.getLogger(__name__)
    log.info("Loaded items: %d", count)      # ✅
    # log.info(f"Loaded items: {count}")     # ❌
    ```

### Reflex UI
- Small components; separate **state** from **view**.
- Deterministic state transitions; avoid hidden side effects.
- Reuse components; document patterns in **Memory**.

#### Background Tasks
Background tasks (`@rx.event(background=True)`) run in isolation and **cannot be called directly** from other event handlers:

```python
# ❌ WRONG - causes RuntimeError
async for event in self.background_task():
    yield event

# ✅ CORRECT - yield the class method reference
yield MyState.background_task
```

**Event chaining pattern** (state update → background task):
```python
@rx.event
async def my_handler(self) -> AsyncGenerator[Any, Any]:
    # 1. Update state synchronously
    self.some_value = "new"
    # 2. Yield to flush state to frontend (optional)
    yield
    # 3. Yield background task as next scheduled event
    yield MyState.background_task
```

### Quality Gates
- Lint/format/type: `task lint`, `task format`.
- Tests: `task test` with coverage ≥ **80%**.


### Commit & PR
- Conventional Commits (`feat:`, `fix:`, `refactor:`…).
- PR must include: description, `Closes #123`, UI screenshots, migration rationale.

### Learn
- Reflect; extract learnings; write to **Memory**.

---

## 5) Code Generation Rules
- **Python 3.13** only; deps via **uv**.
- Use Reflex, Alembic, SQLAlchemy 2.0, FastAPI, Pydantic, FastMCP, LangChain.
- **No f-strings in logger calls.**
- Clean code; narrow modules; clear boundaries. Use design patterns where appropriate.
- Unit tests for every new path.

---

## 6) Testing Strategy
- Tests in `tests/test_*.py`; isolate units; avoid coupling.
- Coverage target **≥ 80%**.
- Write regression tests first when fixing bugs.
- Use fixtures for env/config swaps.

## 7) Search SOPs
- **Context7 first** for framework truths; cite sources in **Memory**.
- **DuckDuckGo** for cross-version issues; prefer official docs, well-known repos.
- Capture only the **final answer** in **Memory**: minimal snippet + rationale + version pins + link.

## 8) Security & Config Hygiene
- No credentials in code/history; use `.env` locally, Key Vault in prod.
- Prefer non-secret YAML; override with env `__` pattern.
- Parameterized logs; avoid sensitive values.
- Update vulnerable deps promptly; document CVE-driven updates in commits and **Memory**.

---

## 9) Pre‑PR Checklist
- [ ] Tests added/updated; all green
- [ ] Lint/format/type checks pass
- [ ] Migrations reviewed & documented
- [ ] **Memory updated** (decisions, patterns, error→fix links)
- [ ] PR description complete; links/screenshots added


---

# Project Architecture

This is a **Reflex component library** wrapping [Mantine UI v8.3.3](https://mantine.dev) for Python web apps. Structure:

- `appkit_mantine/` – Core component wrappers (Input, DateInput, NumberInput, PasswordInput, Textarea, NavigationProgress, etc.)
- `appkit_mantine/base.py` – Base classes (`MantineComponentBase`, `MantineInputComponentBase`) with inheritance hierarchy
- `app/` – Demo app with example pages showing component usage patterns
- `docs/` – Comprehensive usage guides and API references
- `assets/` – JavaScript shims for Mantine integration (MantineProvider, NavigationProgress)

### Key Design Principle: Inheritance-Based Architecture

**ALL Mantine input components inherit from `MantineInputComponentBase`**, eliminating code duplication:

```python
# Base class provides ~40 common props for free
class MantineInputComponentBase(MantineComponentBase):
    # Input.Wrapper props (label, description, error, required, with_asterisk)
    # Visual variants (variant, size, radius)
    # State props (value, default_value, placeholder, disabled)
    # HTML attributes (name, id, aria_label, max_length, pattern, etc.)
    # Section props (left_section, right_section with widths and pointer_events)
    # Mantine style props (w, maw, m, mt, mb, ml, mr, mx, my, p, etc.)
    # Event handlers (on_change, on_focus, on_blur, on_key_down, on_key_up)
```

**When creating new components, only define component-specific props:**

```python
# ✅ Correct - only unique props
class NumberInput(MantineInputComponentBase):
    tag = "NumberInput"
    min: Var[int | float] = None
    max: Var[int | float] = None
    decimal_scale: Var[int] = None
    # All common props inherited automatically

# ❌ Wrong - don't redeclare inherited props
class BadInput(MantineInputComponentBase):
    tag = "BadInput"
    label: Var[str] = None  # Already in base class!
    placeholder: Var[str] = None  # Already in base class!
```

## Critical Integration Patterns

### 1. MantineProvider Requirement

**ALL Mantine components MUST be wrapped in `MantineProvider`** - auto-injected via `_get_app_wrap_components()`:

```python
# Automatically wraps app at priority 44
@staticmethod
def _get_app_wrap_components() -> dict[tuple[int, str], rx.Component]:
    return {
        (44, "MantineProvider"): MemoizedMantineProvider.create(),
    }
```

The provider respects Reflex's color mode and injects required CSS. See `mantine/mantine_provider.js`.

### 2. Custom CSS Injection Pattern

Components requiring additional CSS override `_get_custom_code()`:

```python
class NavigationProgress(MantineComponentBase):
    library = "@mantine/nprogress@8.3.3"

    def _get_custom_code(self) -> str:
        return """import '@mantine/core/styles.css';
import '@mantine/nprogress/styles.css';
import { nprogress } from '@mantine/nprogress';

// Expose API globally for Reflex control
if (typeof window !== 'undefined') {
    window.nprogress = nprogress;
}"""
```

### 3. Event Handler Transformations

Some Mantine components send raw values instead of events - transform via `get_event_triggers()`:

```python
# NumberInput sends number directly, not event.target.value
class NumberInput(MantineInputComponentBase):
    on_change: EventHandler[lambda value: [value]] = None
    # Receives number directly, not event object

# DateInput sends null when cleared - convert to empty string for Reflex state
def _date_input_on_change(value: Var) -> list[Var]:
    return [rx.Var(f"({value} ?? '')", _var_type=str)]

class DateInput(MantineDateInputBase):
    def get_event_triggers(self) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": _date_input_on_change,
        }
```

### 4. External Library Dependencies

Declare via `lib_dependencies` for NPM packages:

```python
class IMaskInput(rx.Component):
    library = "react-imask@7.6.1"
    lib_dependencies: list[str] = ["react-imask@7.6.1"]

class DateInput(MantineDateInputBase):
    library = "@mantine/dates@^8.3.3"
    lib_dependencies: list[str] = ["dayjs@1.11.13"]
```

## Development Workflow

### Running the Demo App

```bash
# Start Reflex dev server (auto-reload enabled)
task run

# Or with debug logging
task run:debug
```

Access demo pages:
- `/` - Index with navigation links
- `/password` - PasswordInput examples
- `/date` - DateInput examples
- `/number` - NumberInput examples
- `/textarea` - Textarea examples
- `/inputs` - Input component showcase
- `/nprogress` - NavigationProgress examples

### Creating New Components

1. **Determine base class:**
   - Input-like? Extend `MantineInputComponentBase`
   - General Mantine? Extend `MantineComponentBase`
   - External library? Extend `rx.Component`

2. **Implement minimal component:**

```python
from mantine.base import MantineInputComponentBase

class MyInput(MantineInputComponentBase):
    tag = "MyInput"  # React component name
    alias = "MantineMyInput"  # Optional: avoid name collisions

    # Only component-specific props
    custom_prop: Var[str] = None
    special_mode: Var[bool] = None

# Export convenience function
my_input = MyInput.create
```

3. **Add to `mantine/__init__.py`:**

```python
from mantine.my_input import MyInput, my_input

__all__ = ["MyInput", "my_input", ...]
```

4. **Create example page in `app/pages/examples/`:**

```python
import reflex as rx
import appkit_mantine as mn

class MyInputState(rx.State):
    value: str = ""

    def set_value(self, val: str) -> None:
        self.value = val

def my_input_page() -> rx.Component:
    return mn.stack(
        mn.title("MyInput Examples"),
        mn.input(
            label="Example",
            value=MyInputState.value,
            on_change=MyInputState.set_value,
        ),
    )
```

5. **Register page in your application (e.g. `app/app.py`):**

```python
from app.pages.examples.my_input_examples import my_input_page

# Then add the page to your Reflex app:
app.add_page(my_input_page, title="My Input", route="/myinput")
```

### Testing Components

Verify inheritance didn't break existing props:

```python
# All inherited props should work
mn.input(
    label="Test",  # From MantineInputComponentBase
    required=True,  # From MantineInputComponentBase
    left_section=rx.icon("search"),  # From MantineInputComponentBase
    custom_prop="works",  # Your specific prop
)
```

## Common Patterns from Examples

### State Management with Validation

```python
class InputState(rx.State):
    username: str = ""
    username_error: str = ""

    @rx.event
    async def validate_username(self) -> AsyncGenerator[Any, Any]:
        if len(self.username) < 3:
            self.username_error = "Must be at least 3 characters"
        else:
            self.username_error = ""
            yield rx.toast.success("Valid!", position="top-right")
```

### Controlled vs Uncontrolled Components

```python
# ✅ Controlled - value managed by state
mn.input(value=State.value, on_change=State.set_value)

# ✅ Uncontrolled - uses default_value
mn.input(default_value="Initial")

# ⚠️ IMaskInput is ALWAYS uncontrolled - use on_accept, not value
mn.imask_input(mask="+1 (000) 000-0000", on_accept=State.handle_accept)
```

### Input.Wrapper for Complete Form Fields

```python
# All input components support wrapper props inherited from base
mn.password_input(
    label="Password",
    description="Must be at least 8 characters",
    error=State.password_error,
    required=True,
    with_asterisk=True,  # Show red asterisk
    placeholder="Enter password",
)
```

### Left/Right Sections (Icons, Buttons)

```python
# Inherited from MantineInputComponentBase
mn.input(
    placeholder="Search...",
    left_section=rx.icon("search"),
    left_section_pointer_events="none",  # Click-through
    right_section=rx.button("Clear", on_click=State.clear),
    right_section_pointer_events="all",  # Clickable
)
```

## Code Quality Standards

### Type Annotations (Python 3.12+)

```python
from typing import Any, Literal
from reflex.vars.base import Var
from reflex.event import EventHandler

class MyComponent(MantineInputComponentBase):
    # Use Var[] for Reflex props
    variant: Var[Literal["filled", "outlined"]] = None
    max_value: Var[int | float] = None

    # Event handlers with lambda signatures
    on_change: EventHandler[lambda value: [value]] = None
```

### Documentation Standards

Every component should have:
- Module docstring with Mantine docs link
- Class docstring linking to Mantine reference
- Prop comments explaining non-obvious behavior
- Example usage in dedicated page

```python
"""Mantine MyInput component wrapper for Reflex.

Provides advanced input functionality with custom features.
See `my_input()` function for detailed usage and examples.

Documentation: https://mantine.dev/core/my-input/
"""

class MyInput(MantineInputComponentBase):
    """Mantine MyInput component.

    Based on: https://mantine.dev/core/my-input/

    Inherits common input props from MantineInputComponentBase.
    See `my_input()` function for detailed documentation and examples.
    """
```

## Project-Specific Notes

### Why This Structure?

- `pyproject.toml` references non-existent `components/knai-*` packages - **ignore these**, they're from a different project
- `uv.lock` workspace members don't match actual structure - **this is a standalone component library**
- Focus development in `mantine/` package and `reflex_mantine/` demo app only

### Version Management

- Pin versions to avoid breaking changes

### Asset Management

JavaScript shims in `assets/external/mantine/`:
- `base/mantine_provider.js` - Color mode integration
- `nprogress/navigation_progress.js` - Progress bar controls

Reference via `asset(path="<filename.js>", shared=True)` in component `library` prop.

## Rules Recap
🛠️ Tooling & Workflow
- Task Runner: Use task commands (via Taskfile.dist.yml) instead of make.
- Validator: Always run task format after editing files to ensure compliance. This handles both formatting (Black/Ruff) and linting (Ruff).

🐍 Python Code Style (Ruff/Black)
- Line Length: strictly 88 characters.
- Break long function calls, comments, and strings to fit this limit.
- Correction strategy: If replace_string_in_file fails due to line length,
  refactor into multi-line statements before applying.
- Imports: Remove unused imports immediately (F401).
- Type Hints: Avoid redundant unions.
- Bad: Literal["small", "large"] | str (Literal is redundant if str is present).
- Good: str (if open-ended) or Literal["small", "large"] (if closed).
- Arguments: Remove unused function arguments (ARG001) unless required for strict API signature compatibility (in which case, prefix with _).

🏗️ AppKit & Reflex Architecture
- Do not use rx.session() inside background processors, callbacks, or pure Python utilities.
- Do use appkit_commons.database.session_manager.get_session_manager().session() context manager for robust DB access in those contexts.
- Configuration fields often use Pydantic SecretStr. Always access them via .get_secret_value() to retrieve the raw string.
- Use logging.getLogger(__name__).
- No f-strings in logging calls (lazy evaluation). Correct: logger.info("Processing user %s", user_id). Incorrect: logger.info(f"Processing user {user_id}")
- do not use "and", "or" in rx.cond(). Use "&" and "|" instead for proper expression tree generation.
- NEVER user print or printf for logging or debugging. Always use the logging module.
- always use log.debug for detailed internal state information, log.info for high-level process milestones, log.warning for recoverable issues, and log.error for serious problems.
