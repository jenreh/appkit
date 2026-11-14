# appkit-ui

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Shared UI helpers for AppKit applications.**

appkit-ui provides a small set of reusable UI helpers built on Reflex and appkit-mantine: a page header, a delete confirmation dialog, form field helpers, a collapsible section, a global loading state, and a sticky table header style.

---

## 🚀 Installation

### As Part of AppKit Workspace

```bash
git clone https://github.com/jenreh/appkit.git
cd appkit
uv sync
```

### Standalone Installation

```bash
pip install appkit-ui
# or
uv add appkit-ui
```

### Dependencies

- `appkit-mantine` (Mantine components for Reflex)

---

## 📖 Usage

### Header

A fixed page header placed to the right of the sidebar. `header_items` is rendered on the right side.

```python
from appkit_ui.components.header import SIDEBAR_WIDTH, header

header("Application Title")
header("Gallery", header_items=mn.button("New"))
```

`SIDEBAR_WIDTH` is the sidebar width the header offsets itself by.

### Delete Confirmation Dialog

```python
from appkit_ui.components.dialogs import delete_dialog

delete_dialog(
    title="Delete User",
    content="user@example.com",
    on_click=UserState.delete_user,
    icon_button=True,
    action_loading=UserState.is_loading,
)
```

### Form Fields

`form_field` wraps a Mantine input with a label, description, icon and error message. All extra keyword arguments go to the input.

```python
from appkit_ui.components.form_inputs import form_field, hidden_field

form_field(
    icon="server",
    label="Name",
    hint="Unique server name",
    name="name",
    default_value="",
    validation_error=FormState.name_error,
    required=True,
)

hidden_field(name="user_id", default_value="42")
```

### Collapsible Section

```python
from appkit_ui.components.collapsible import collapsible

collapsible(
    rx.text("Details..."),
    title="Details",
    info_text="3 items",
    show_condition=State.has_details,
    expanded=State.details_expanded,
    on_toggle=State.toggle_details,
)
```

### Loading State

```python
from appkit_ui.global_states import LoadingState

rx.link("Users", href="/users", on_click=LoadingState.set_is_loading(True))

rx.box(
    page_content,
    class_name=rx.cond(LoadingState.is_loading, "cursor-wait", ""),
)
```

### Sticky Table Header Style

```python
from appkit_ui.styles import sticky_header_style

mn.table.thead(..., style=sticky_header_style)
```

---

## 📋 API Reference

| Module | Symbol | Purpose |
| --- | --- | --- |
| `appkit_ui.components.header` | `header()`, `SIDEBAR_WIDTH` | Fixed page header |
| `appkit_ui.components.dialogs` | `delete_dialog()` | Confirmation dialog for delete actions |
| `appkit_ui.components.form_inputs` | `form_field()`, `hidden_field()` | Form input helpers |
| `appkit_ui.components.collapsible` | `collapsible()` | Expandable content section |
| `appkit_ui.global_states` | `LoadingState` | Global loading flag |
| `appkit_ui.styles` | `sticky_header_style` | Sticky table header styling |

---

## 📚 Related Components

- **[appkit-mantine](./../appkit-mantine)** - Mantine UI components used throughout appkit-ui
- **[appkit-user](./../appkit-user)** - User authentication components
- **[appkit-commons](./../appkit-commons)** - Shared utilities and configuration
- **[appkit-assistant](./../appkit-assistant)** - AI assistant with UI components
