# State Management Reference

## Contents

- Typing state vars
- Backend-only vars
- Substates
- Computed vars
- Auto-generated setters

## Typing state vars

ALWAYS provide type annotations. Reflex uses them for serialization and diffing.

```python
class UserState(rx.State):
    username: str = ""
    count: int = 0
    items: list[str] = []
    is_loading: bool = False

# Backend-only vars

Prefix with _ to keep vars server-side only. They are never serialized or sent to the frontend.

```python
class DataState(rx.State):
    _db_connection = None      # Never sent to client
    _internal_cache: dict = {} # Server-only computation cache
    display_label: str = ""    # Synced to frontend
````

## Substates

Split large apps into feature substates. Child states only sync their own dirty vars,
reducing unnecessary diffs.

```python
# states/auth_state.py
class AuthState(rx.State):
    is_authenticated: bool = False
    user_id: str = ""

# states/dashboard_state.py
class DashboardState(rx.State):
    metrics: list[dict] = []
    selected_tab: str = "overview"
```

## Computed vars

Use @rx.var for derived values. Add cache=True for expensive derivations that
don't need to recompute on every render.

```python
class CartState(rx.State):
    items: list[dict] = []

    @rx.var(cache=True)
    def total_price(self) -> float:
        return sum(item["price"] for item in self.items)

    @rx.var
    def item_count(self) -> int:
        return len(self.items)  # Cheap, no cache needed
```

## Auto-generated setters

Use the auto-generated State.set_<var> event handler for simple assignments
instead of writing a full event handler.

```python
# Preferred for simple updates

rx.button("Reset", on_click=UserState.set_username(""))

# Only write a handler when additional logic is required
class UserState(rx.State):
    username: str = ""

    def reset_and_notify(self):
        self.username = ""
        return rx.toast.info("Username cleared")
```
