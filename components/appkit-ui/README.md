# appkit-ui

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Shared UI helpers for AppKit applications.**

appkit-ui provides a small set of reusable UI helpers built on Reflex and appkit-mantine: a page header, a form field helper and a collapsible section.

`delete_dialog`, `LoadingState` and `sticky_header_style` moved to appkit-mantine (`mn.delete_dialog`, `mn.LoadingState`, `mn.sticky_header_style`).

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

### Form Fields

`form_field` wraps a Mantine input with a label, description, icon and error message. All extra keyword arguments go to the input.

```python
from appkit_ui.components.form_inputs import form_field

form_field(
    icon="server",
    label="Name",
    hint="Unique server name",
    name="name",
    default_value="",
    validation_error=FormState.name_error,
    required=True,
)
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

---

## 📋 API Reference

| Module | Symbol | Purpose |
| --- | --- | --- |
| `appkit_ui.components.header` | `header()`, `SIDEBAR_WIDTH` | Fixed page header |
| `appkit_ui.components.form_inputs` | `form_field()` | Form input helper |
| `appkit_ui.components.collapsible` | `collapsible()` | Expandable content section |

---

## 📚 Related Components

- **[appkit-mantine](./../appkit-mantine)** - Mantine UI components used throughout appkit-ui
- **[appkit-user](./../appkit-user)** - User authentication components
- **[appkit-commons](./../appkit-commons)** - Shared utilities and configuration
- **[appkit-assistant](./../appkit-assistant)** - AI assistant with UI components
