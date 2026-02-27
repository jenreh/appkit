# Performance Reference

## Contents

- Background tasks for async I/O
- Streaming updates with yield
- Component rendering rules
- Multi-instance / Redis config

## Background tasks for async I/O

Use `@rx.background` for any network calls, DB queries, or long computations.
Always acquire state with `async with self:` before mutating.

```python
class DataState(rx.State):
    data: list = []
    is_loading: bool = False

    @rx.background
    async def fetch_data(self):
        async with self:
            self.is_loading = True
        result = await some_api_call()
        async with self:
            self.data = result
            self.is_loading = False
```

## Streaming updates with yield

Use yield inside regular event handlers to push incremental updates to the frontend.

```python
class StreamState(rx.State):
    output: str = ""

    def stream_response(self):
        for chunk in llm_stream():
            self.output += chunk
            yield
```

## Component rendering rules

NEVER use bare Python if inside component functions. Use rx.cond and rx.foreach.

```python
# CORRECT
def item_list() -> rx.Component:
    return rx.vstack(
        rx.cond(
            ListState.is_empty,
            rx.text("No items"),
            rx.foreach(ListState.items, render_item),
        ),
    )

# WRONG — won't react to state changes
def item_list() -> rx.Component:
    if ListState.is_empty:  # Static evaluation at import time!
        return rx.text("No items")
    return rx.vstack(...)
```

## Multi-instance / Redis config

For Kubernetes or multi-pod deployments, configure Redis in rxconfig.py.
The default in-memory state manager does not work across replicas.

```python
# rxconfig.py
import reflex as rx

config = rx.Config(
    app_name="myapp",
    api_url="https://api.yourdomain.com",
    redis_url="redis://redis-service:6379",
    env=rx.Env.PROD,
)
```
