# Testing Strategy

## Coverage requirements

| Code Category | Coverage Target | Test Location |
| --- | --- | --- |
| Non-Reflex classes (services, repos, models, utilities) | **≥ 80%** | `tests/` |
| Reflex State classes (event handlers, computed vars) | **≥ 80%** | `tests/` |
| Reflex UI components (rendering) | Best-effort | Not required |
| Alembic migrations | Manual review | Not required |

## Test structure

- Tests in `tests/test_*.py`; isolate units; avoid coupling.
- Write regression tests first when fixing bugs.
- Use fixtures for env/config swaps.
- Use factory patterns for test data (not raw dicts).

## Testing Reflex State

Reflex `State` is a plain Python class — test directly with `pytest` and `pytest-asyncio`:

```python
import pytest

@pytest.fixture
def state():
    return MyState()

# Sync handlers
def test_increment(state):
    state.increment()
    assert state.count == 1

# Async handlers
async def test_fetch_data(state):
    await state.fetch_data()
    assert len(state.items) > 0
    assert state.is_loading is False

# Streaming handlers
async def test_streaming(state):
    async for _ in state.stream_results():
        pass
    assert state.result_text != ""

# Computed vars
def test_item_count(state):
    state.items = ["x", "y", "z"]
    assert state.item_count == 3

# UI handlers receiving str|list[str]
def test_set_tab_str(state):
    state.set_tab_control("overview")
    assert state.tab_control == "overview"

def test_set_tab_list(state):
    state.set_tab_control(["overview"])
    assert state.tab_control == "overview"

# External I/O — mock at module path
async def test_save_success(state):
    with patch("myapp.state.api_client.post", new_callable=AsyncMock) as m:
        m.return_value = {"id": "abc"}
        await state.save_item("new_item")
        m.assert_called_once()
        assert state.last_saved_id == "abc"

# Background tasks — patch context manager
async def test_background_task(state):
    with patch.object(state, "__aenter__", return_value=state), \
         patch.object(state, "__aexit__", return_value=False):
        async for _ in state.long_running_task():
            pass
    assert state.progress == 100
```

## Running tests

```bash
task test                           # Full suite with coverage
uv run pytest tests -k assistant    # Targeted runs
uv run pytest tests -x              # Stop on first failure
```

## Pytest multi-testpath setup

When the project has two `tests/` directories (e.g. root `tests/` and component `tests/`), both must be registered or `ImportPathMismatchError` will occur:

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests", "components/alloq-commons/tests"]
addopts = "--import-mode=importlib"
```

- Remove `__init__.py` from **component** test directories (but keep it in the root `tests/`).
- Set `import_mode = "importlib"` — this is the key fix for the mismatch.

## Async SQLite testing dependency

For async in-memory SQLite tests (e.g. `sqlite+aiosqlite://`):

```bash
uv pip install aiosqlite
```

Add to `[project.optional-dependencies]` or `[dependency-groups]` in `pyproject.toml` so it's always available in CI.
