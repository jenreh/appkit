# appkit-mantine

[![PyPI version](https://badge.fury.io/py/appkit-mantine.svg)](https://badge.fury.io/py/appkit-mantine)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Pre-release](https://img.shields.io/badge/status-pre--release-orange.svg)](https://github.com/jenreh/reflex-mantine)

**reflex.dev components based on MantineUI**

A Reflex wrapper library focusing on [Mantine UI v8.3.3](https://mantine.dev) input components, designed for building robust forms and data entry interfaces in Python web applications.

---

## ✨ Features

- **🎯 Input-Focused** - Comprehensive coverage of form inputs: text, password, number, date, masked inputs, textarea, and rich text editor
- **🔒 Type-Safe** - Full type annotations with IDE autocomplete support for all props and event handlers
- **📚 Rich Examples** - Production-ready code examples for every component with common patterns and edge cases
- **🏗️ Clean Architecture** - Inheritance-based design eliminating code duplication across 40+ common props
- **🎨 Mantine Integration** - Seamless integration with Mantine's theming, color modes, and design system
- **⚡ Modern Stack** - Built on Reflex 0.8.13+ with React 18 and Mantine 8.3.3

---

## 📦 Installation

### Using pip

```bash
pip install appkit-mantine
```

### Using uv (recommended)

```bash
uv add appkit-mantine
```

### Development Installation

For local development or to run the demo application:

```bash
# Clone the repository
git clone https://github.com/jenreh/appkit.git
cd appkit

# Install with uv (installs workspace components)
uv sync

# Run the demo app
reflex run
```

> **⚠️ Pre-release Notice:** This library is in development. APIs may change before the 1.0 release.

---

## 🚀 Quick Start

```python
import reflex as rx
import appkit_mantine as mn

class FormState(rx.State):
    email: str = ""
    password: str = ""

def login_form() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Login"),

            # Basic input with validation
            mn.form.input(
                label="Email",
                placeholder="you@example.com",
                value=FormState.email,
                on_change=FormState.set_email,
                required=True,
                type="email",
            ),

            # Password input with visibility toggle
            mn.password_input(
                label="Password",
                value=FormState.password,
                on_change=FormState.set_password,
                required=True,
            ),

            rx.button("Sign In", on_click=FormState.handle_login),
            spacing="4",
        ),
        max_width="400px",
    )

app = rx.App()
app.add_page(login_form)
```

---

## 📋 Available Components

### Inputs

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **`text_input`** | Basic text input / text inputs showcase | [Guide](docs/MANTINE_INPUTS_GUIDE.md) |
| **`input`** | Polymorphic base input element with sections, variants, sizes | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/input_examples.py) |
| **`password_input`** | Password field with visibility toggle | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/password_input_examples.py) |
| **`date_input`** | Date picker with range constraints and formatting | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/date_input_examples.py) |
| **`number_input`** | Numeric input with formatting, min/max, step controls | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/number_input_examples.py) |
| **`textarea`** | Multi-line text input with auto-resize | [Guide](docs/MANTINE_TEXTAREA_GUIDE.md) |
| **`json_input`** | JSON input with formatting, validation, parser, pretty printing | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/json_input_examples.py) |
| **`select`** | Dropdown select with data array, inherits input props | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/select_examples.py) |
| **`multi_select`** | Multi-select dropdown for selecting multiple values | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/multi_select_examples.py) |
| **`rich_select`** | Advanced select component with search and grouping | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/rich_select_examples.py) |
| **`tags_input`** | Free-form tags input component | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/tags_input_examples.py) |
| **`autocomplete`** | Autocomplete input with string data array | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/autocomplete_examples.py) |
| **`rich_text_editor`** | WYSIWYG editor powered by Tiptap | [Guide](docs/MANTINE_TIPTAP_GUIDE.md) |
| **`masked_input`** | Input masking for phone numbers, credit cards, custom patterns | [Guide](docs/MANTINE_INPUTS_GUIDE.md) |

### Buttons

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **`action_icon`** | Lightweight button for icons with size, variant, radius, disabled state | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/action_icon_examples.py) |
| **`button`** | Button with variants, sizes, gradient, loading states, sections | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/button_examples.py) |

### Overlays

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **`modal`** | Accessible overlay dialog with focus trap and scroll lock | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/modal_examples.py) |
| **`drawer`** | Overlay drawer area sliding from any side | [Docs](https://mantine.dev/core/drawer/) |

### Others

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **`markdown_preview`** | Markdown renderer with Mermaid diagrams and math support | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/markdown_preview_examples.py) |
| **`navigation_progress`** | Page loading progress indicator | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/nprogress_examples.py) |
| **`nav_link`** | Navigation link with label, description, icons, nested links, active/disabled states | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/nav_link_examples.py) |
| **`number_formatter`** | Formats numeric input with parser/formatter, returns parsed value | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/number_formatter_examples.py) |
| **`scroll_area`** | Scrollable container with custom scrollbars and virtualization | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/scroll_area_examples.py) |
| **`table`** | Table component for tabular data display | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/table_examples.py) |

### Common Props (Inherited by All Inputs)

All input components inherit ~40 common props from `MantineInputComponentBase`:

```python
# Input.Wrapper props
label="Field Label"
description="Helper text"
error="Validation error"
required=True
with_asterisk=True  # Show red asterisk for required fields

# Visual variants
variant="filled"  # "default" | "filled" | "unstyled"
size="md"  # "xs" | "sm" | "md" | "lg" | "xl"
radius="md"  # "xs" | "sm" | "md" | "lg" | "xl"

# State management
value=State.field_value
default_value="Initial value"
placeholder="Enter text..."
disabled=False

# Sections (icons, buttons)
left_section=rx.icon("search")
right_section=rx.button("Clear")
left_section_pointer_events="none"  # Click-through

# Mantine style props
w="100%"  # width
maw="500px"  # max-width
m="md"  # margin
p="sm"  # padding

# Event handlers
on_change=State.handle_change
on_focus=State.handle_focus
on_blur=State.handle_blur
```

## 📖 Usage Examples

### Basic Input with Validation

```python
import reflex as rx
import appkit_mantine as mn

class EmailState(rx.State):
    email: str = ""
    error: str = ""

    def validate_email(self):
        if "@" not in self.email:
            self.error = "Invalid email format"
        else:
            self.error = ""

def email_input():
    return mn.form.input(
        label="Email Address",
        description="We'll never share your email",
        placeholder="you@example.com",
        value=EmailState.email,
        on_change=EmailState.set_email,
        on_blur=EmailState.validate_email,
        error=EmailState.error,
        required=True,
        type="email",
        left_section=rx.icon("mail"),
    )
```

### Number Input with Formatting

```python
class PriceState(rx.State):
    price: float = 0.0

def price_input():
    return mn.number_input(
        label="Product Price",
        value=PriceState.price,
        on_change=PriceState.set_price,
        prefix="$",
        decimal_scale=2,
        fixed_decimal_scale=True,
        thousand_separator=",",
        min=0,
        max=999999.99,
        step=0.01,
    )
```

### Masked Input (Phone Number)

```python
class PhoneState(rx.State):
    phone: str = ""

def phone_input():
    return mn.masked_input(
        label="Phone Number",
        mask="+1 (000) 000-0000",
        value=PhoneState.phone,
        on_accept=PhoneState.set_phone,  # Note: on_accept, not on_change
        placeholder="+1 (555) 123-4567",
    )
```

### Date Input with Constraints

```python
from datetime import date, timedelta

class BookingState(rx.State):
    checkin: str = ""

def date_picker():
    today = date.today()
    max_date = today + timedelta(days=365)

    return mn.date_input(
        label="Check-in Date",
        value=BookingState.checkin,
        on_change=BookingState.set_checkin,
        min_date=today.isoformat(),
        max_date=max_date.isoformat(),
        clear_button_props={"aria_label": "Clear date"},
    )
```

### Rich Text Editor

```python
class EditorState(rx.State):
    content: str = "<p>Start typing...</p>"

def editor():
    return mn.rich_text_editor(
        value=EditorState.content,
        on_change=EditorState.set_content,
        toolbar_config=mn.EditorToolbarConfig(
            controls=[
                mn.ToolbarControlGroup.FORMATTING,
                mn.ToolbarControlGroup.LISTS,
                mn.ToolbarControlGroup.LINKS,
            ]
        ),
    )
```

### Action Icon

```python
def action_icon_example():
    return mn.action_icon(
        rx.icon("heart"),
        variant="filled",
        color="red",
        size="lg",
        on_click=State.like_item,
    )
```

### Autocomplete

```python
class SearchState(rx.State):
    query: str = ""

def autocomplete_example():
    return mn.autocomplete(
        label="Search",
        placeholder="Type to search...",
        data=["Apple", "Banana", "Cherry"],
        value=SearchState.query,
        on_change=SearchState.set_query,
    )
```

### Button

```python
def button_example():
    return mn.button(
        "Click me",
        variant="gradient",
        gradient={"from": "blue", "to": "cyan"},
        size="lg",
        on_click=State.handle_click,
    )
```

### Combobox

```python
def combobox_example():
    return mn.combobox(
        label="Select option",
        data=[
            {"value": "react", "label": "React"},
            {"value": "vue", "label": "Vue"},
        ],
        on_option_submit=State.set_selected,
    )
```

### Input

```python
def input_example():
    return mn.input(
        placeholder="Enter text...",
        left_section=rx.icon("search"),
        right_section=rx.button("Clear"),
    )
```

### JSON Input

```python
class JsonState(rx.State):
    data: str = '{"name": "example"}'

def json_input_example():
    return mn.json_input(
        label="JSON Data",
        value=JsonState.data,
        on_change=JsonState.set_data,
        format_on_blur=True,
    )
```

### Nav Link

```python
def nav_link_example():
    return mn.nav_link(
        label="Dashboard",
        left_section=rx.icon("home"),
        active=True,
        on_click=State.navigate_to_dashboard,
    )
```

### Number Formatter

```python
class PriceState(rx.State):
    amount: float = 1234.56

def number_formatter_example():
    return mn.number_formatter(
        value=PriceState.amount,
        prefix="$",
        thousand_separator=",",
        decimal_scale=2,
    )
```

### Select

```python
class SelectState(rx.State):
    choice: str = ""

def select_example():
    return mn.select(
        label="Choose one",
        data=["Option 1", "Option 2", "Option 3"],
        value=SelectState.choice,
        on_change=SelectState.set_choice,
    )
```

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
