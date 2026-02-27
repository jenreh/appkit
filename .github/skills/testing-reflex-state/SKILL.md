---
name: testing-reflex-state
description: Generates pytest unit tests for Reflex.dev state logic — event handlers, computed vars, substates, and mocked external dependencies. Use when the user asks to write, scaffold, or review tests for a Reflex State class. Do NOT use for Playwright integration tests or UI component rendering tests.
---

# Testing Reflex State

Reflex `State` is a plain Python class — no browser or runtime needed.
Test it directly with `pytest` and `pytest-asyncio`.

## Setup

```bash
pip install pytest pytest-asyncio pytest-cov
```

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests/unit"]
asyncio_mode = "auto"
python_files = ["test_*.py"]
```

## File layout

```
tests/unit/
├── conftest.py
├── test_base_state.py
└── test_project_state.py
```

## Patterns

**Base vars** → test defaults directly
**Sync handlers** → call on instance, assert result
**Async handlers** → `await`, assert `is_loading is False` after
**Streaming handlers** → consume with `async for`
**Computed vars** → mutate base vars, assert property
**Substates** → instantiate subclass independently
**External I/O** → `unittest.mock.patch` at `myapp.state.*`
**Background tasks** → patch `__aenter__`/`__aexit__`

See [references/PATTERNS.md](references/PATTERNS.md) for full code examples.
See [references/FIXTURES.md](references/FIXTURES.md) for shared fixture setup.

## Decision: which pattern to use?

**Sync handler?** → Test directly, no `async`
**Async handler?** → Use `await`, check loading flag resets
**Handler bound to Radix UI component?** → Add `str` AND `list[str]` test cases
**Handler calls API/DB?** → Mock with `AsyncMock`, test both success and failure
**Background task (`@rx.event(background=True)`)?** → Patch context manager

## Run

```bash
pytest tests/unit/ -v --cov=myapp/state --cov-report=term-missing
pytest tests/unit/test_project_state.py -v   # single module
pytest tests/unit/ -x                        # stop on first failure
```
