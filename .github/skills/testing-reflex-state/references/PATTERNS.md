# Code Patterns

## Base var defaults

```python
def test_initial_values(state):
    assert state.count == 0
    assert state.is_loading is False
    assert state.items == []
```

## Sync event handlers

```python
def test_increment(state):
    state.increment()
    assert state.count == 1

def test_reset(state):
    state.count = 99
    state.reset_counter()
    assert state.count == 0
```

## UI handlers (str | list[str] guard)

```python
def test_set_tab_str(state):
    state.set_tab_control("overview")
    assert state.tab_control == "overview"

def test_set_tab_list(state):
    state.set_tab_control(["overview"])
    assert state.tab_control == "overview"
```

## Async event handlers

```python
async def test_fetch_data(state):
    await state.fetch_data()
    assert len(state.items) > 0
    assert state.is_loading is False

async def test_fetch_resets_on_error(state):
    state.api_url = "http://invalid"
    await state.fetch_data()
    assert state.is_loading is False
```

## Streaming handlers

```python
async def test_streaming(state):
    async for _ in state.stream_results():
        pass
    assert state.result_text != ""
```

## Computed vars

```python
def test_item_count(state):
    state.items = ["x", "y", "z"]
    assert state.item_count == 3

def test_is_empty(state):
    state.items = []
    assert state.is_empty is True
```

## Substates

```python
from myapp.state import ProjectState

def test_select_project():
    s = ProjectState()
    s.select_project("proj-123")
    assert s.selected_project == "proj-123"
```

## Mocked external I/O

```python
from unittest.mock import patch, AsyncMock

async def test_save_success(state):
    with patch("myapp.state.api_client.post", new_callable=AsyncMock) as m:
        m.return_value = {"id": "abc"}
        await state.save_item("new_item")
        m.assert_called_once()
        assert state.last_saved_id == "abc"

async def test_save_failure(state):
    with patch("myapp.state.api_client.post", side_effect=Exception("timeout")):
        await state.save_item("bad_item")
        assert state.error_message == "timeout"
        assert state.is_loading is False
```

## Background tasks

```python
async def test_background_task(state):
    with patch.object(state, "__aenter__", return_value=state), \
         patch.object(state, "__aexit__", return_value=False):
        async for _ in state.long_running_task():
            pass
    assert state.progress == 100
```
