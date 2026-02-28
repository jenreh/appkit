---
name: writing-python-code
description: Enforces Python 3.13 code style, logging rules, type annotations, design patterns, testing strategy, and clean code principles for the appkit project. Use when writing, reviewing, or refactoring Python code, creating new modules, or adding tests.
license: MIT
metadata:
  author: jens-rehpoehler
  version: "1.0"
---

# Writing Python Code

## Quick reference

- **Python 3.13** only; deps via **uv**; line length **88** chars (Ruff/Black).
- **No f-strings in logger calls** — use `log.info("x: %s", val)`.
- **Type annotations** on every function and method.
- **Files ≤ 1000 lines** — refactor via Extract Class, Mixins, Strategy, etc.
- **Coverage ≥ 80%** for non-Reflex classes and Reflex State classes.
- **Task runner:** `task format`, `task lint`, `task test` (not `make`).

## Code style

### Logging

```python
import logging

log = logging.getLogger(__name__)

log.info("Loaded items: %d", count)          # ✅ parameterized
# log.info(f"Loaded items: {count}")         # ❌ f-string
```

Never use `print` or `printf`. Log levels: `debug` → internal state, `info` → milestones, `warning` → recoverable, `error` → serious.

### Type hints

```python
def process(data: dict[str, Any], count: int = 0) -> list[str]: ...

async def handler(value: str) -> AsyncGenerator[Any, Any]:
    yield
```

- Do not mix `Literal[...]` with `str` — pick one.
- Remove unused imports immediately (F401).
- Remove unused args or prefix with `_` (ARG001).

### Imports & formatting

- Ruff handles lint + format; run `task format` before committing.
- Break long calls/strings to fit 88 chars.

## File size rule

No Python file may exceed **1000 lines**. When approaching the limit, apply clean code refactoring strategies.

**Design patterns & refactoring strategies:** See [references/clean-code.md](references/clean-code.md).

## Testing

Coverage target: **≥ 80%** for services, repositories, models, utilities, and Reflex State classes. UI component rendering is best-effort.

```bash
task test                           # full suite with coverage
uv run pytest tests -k assistant    # targeted
uv run pytest tests -x              # stop on first failure
```

**Test patterns, fixtures, Reflex State testing:** See [references/testing.md](references/testing.md).

## Security & config

- No credentials in code/history; use `.env` locally, Key Vault in prod.
- Access Pydantic `SecretStr` via `.get_secret_value()`.
- Parameterized logs; avoid sensitive values.
- Use `appkit_commons.database.session_manager.get_session_manager().session()` for DB access outside Reflex handlers (not `rx.session()`).

## Database operations

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()
```

- Do NOT use `--autogenerate` for Alembic migrations; write them manually.
- BaseRepository methods must not commit; transaction boundaries are owned by the caller.

## Workflow

1. `task sync` to install/update deps.
2. Write or adjust tests first (`tests/test_*.py`).
3. Implement minimal diff.
4. `task format && task lint && task test`.
5. Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `chore:`.

## Pre-commit checklist

- [ ] Tests pass (`task test`)
- [ ] Coverage ≥ 80%
- [ ] Lint/format clean (`task format && task lint`)
- [ ] No file exceeds 1000 lines
- [ ] No secrets in code
- [ ] Logging uses parameterized formatting
- [ ] All functions have type annotations
