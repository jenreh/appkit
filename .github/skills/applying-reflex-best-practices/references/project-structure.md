# Project Structure Reference

## Contents

- Canonical layout
- Naming conventions
- Page registration
- rxconfig.py checklist

## Canonical layout

myapp/
├── rxconfig.py
├── requirements.txt
├── app/
│ ├── app.py # Only page registration + app init
│ ├── pages/
│ │ ├── index.py
│ │ ├── dashboard.py
│ │ └── settings.py
│ ├── states/
│ │ ├── auth_state.py
│ │ ├── dashboard_state.py
│ │ └── settings_state.py
│ └── components/
│ ├── navbar.py
│ └── data_table.py

## Naming conventions

- State classes: `PascalCase` ending with `State` → `DashboardState`
- Pages: `snake_case` function returning `rx.Component` → `def dashboard_page()`
- Components: `snake_case` functions → `def user_card()`
- State vars: `snake_case` → `is_loading`, `user_name`
- Private/backend vars: leading underscore → `_db_cursor`

## Page registration

```python
# app.py
import reflex as rx
from myapp.pages.index import index_page
from myapp.pages.dashboard import dashboard_page

app = rx.App()
app.add_page(index_page, route="/")
app.add_page(dashboard_page, route="/dashboard")
```

## rxconfig.py checklist

```python
import reflex as rx

config = rx.Config(
    app_name="myapp",
    api_url="https://api.yourdomain.com",   # Always set explicitly
    env=rx.Env.PROD,                         # Use PROD in production
    # redis_url="redis://...",              # Required for multi-instance
)
```

- Pin Reflex version: reflex==0.x.x in pyproject.toml
- Set PROD env to disable hot reload and enable optimized builds
- Explicitly set api_url — misconfiguration is the most common deployment failure
