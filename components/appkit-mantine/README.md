# appkit-mantine

[![PyPI version](https://badge.fury.io/py/appkit-mantine.svg)](https://badge.fury.io/py/appkit-mantine)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**reflex.dev components based on MantineUI**

A Reflex wrapper library exposing the full [Mantine UI v9.4.1](https://mantine.dev) component suite — inputs, buttons, overlays, navigation, layout, data display, feedback, charts, maps, scheduling and more — for building robust, type-safe Python web applications.

---

## ✨ Features

- **🧩 Full Component Coverage** - 90+ components across inputs, buttons, overlays, navigation, layout, data display, feedback, charts, maps, scheduling, and typography
- **🔒 Type-Safe** - Full type annotations with IDE autocomplete support for all props and event handlers (`.pyi` stubs for every component)
- **📚 Rich Examples** - Production-ready code examples for every component with common patterns and edge cases
- **🏗️ Clean Architecture** - Inheritance-based design (`MantineComponentBase` → `MantineLayoutComponentBase` → `MantineInputComponentBase`) eliminating code duplication across ~40 common props
- **🎨 Mantine Integration** - Seamless integration with Mantine's theming, color modes, and design system; `MantineProvider` is auto-injected
- **⚡ Modern Stack** - Built on Reflex 0.9.6+ with React 18 and Mantine 9.4.1

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
| **`password_input`** | Password field with visibility toggle | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/input_examples.py) |
| **`number_input`** | Numeric input with formatting, min/max, step controls | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/input_examples.py) |
| **`textarea`** | Multi-line text input with auto-resize | [Guide](docs/MANTINE_TEXTAREA_GUIDE.md) |
| **`json_input`** | JSON input with formatting, validation, parser, pretty printing | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/input_examples.py) |
| **`masked_input`** | Input masking for phone numbers, credit cards, custom patterns (uncontrolled) | [Guide](docs/MANTINE_INPUTS_GUIDE.md) |
| **`color_input` / `color_picker`** | Color entry and swatch picker | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/inputs_advanced_examples.py) |
| **`file_input` / `dropzone`** | File selection input and drag-and-drop upload zone | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/inputs_advanced_examples.py) |
| **`rating`, `pin_input`, `chip`, `fieldset`** | Additional form primitives | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/inputs_advanced_examples.py) |
| **`checkbox`, `radio`, `switch`, `segmented_control`** | Toggle-style inputs | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/inputs_advanced_examples.py) |
| **`slider`, `range_slider`, `hue_slider`, `alpha_slider`, `angle_slider`** | Slider family | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/inputs_advanced_examples.py) |
| **`select`, `multi_select`, `autocomplete`, `combobox`, `tags_input`, `tree_select`** | Selection and combobox-based inputs | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/combobox_examples.py) |
| **`rich_select`** | Advanced select component with search and grouping | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/combobox_examples.py) |
| **`date_input`, `date_picker`, `date_picker_input`, `date_time_picker`, `time_input`, `time_picker`, `month_picker`, `year_picker`, `calendar`** | Full date/time picker family | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/date_examples.py) |
| **`rich_text_editor`** | WYSIWYG editor powered by Tiptap | [Guide](docs/MANTINE_TIPTAP_GUIDE.md) |

### Buttons

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **`action_icon`** | Lightweight button for icons with size, variant, radius, disabled state | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/button_examples.py) |
| **`button`** | Button with variants, sizes, gradient, loading states, sections | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/button_examples.py) |
| **`close_button`, `unstyled_button`** | Additional button variants | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/button_examples.py) |

### Overlays

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **`modal`** | Accessible overlay dialog with focus trap and scroll lock | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/modal_examples.py) |
| **`drawer`** | Overlay drawer area sliding from any side | [Docs](https://mantine.dev/core/drawer/) |
| **`alert_dialog`** | Confirmation/alert dialog with focus management | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/alert_dialog_examples.py) |
| **`popover`, `hover_card`, `tooltip`, `dialog`, `overlay`, `loading_overlay`** | Contextual overlays | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/overlay_examples.py) |
| **`menu`, `menubar`** | Dropdown and application menus | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/menu_examples.py) |

### Navigation & Layout

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **`nav_link`, `tabs`, `breadcrumbs`, `pagination`, `stepper`, `anchor`, `burger`, `table_of_contents`** | Navigation primitives | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/navigation_examples.py) |
| **`navigation_progress`** | Page loading progress indicator | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/nprogress_examples.py) |
| **`app_shell`, `container`, `stack`, `group`, `grid`, `simple_grid`, `flex`, `center`, `space`, `divider`, `affix`, `scroller`, `splitter`** | Layout building blocks | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/layout_examples.py) |
| **`scroll_area`** | Scrollable container with custom scrollbars and virtualization | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/scroll_area_examples.py) |

### Data Display & Feedback

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **`table`** | Table component for tabular data display | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/table_examples.py) |
| **`accordion`, `avatar`, `badge`, `card`, `data_list`, `empty_state`, `image`, `indicator`, `kbd`, `paper`, `spoiler`, `theme_icon`, `timeline`** | Data display components | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/data_display_examples.py) |
| **`alert`, `loader`, `notification`, `progress`, `ring_progress`, `skeleton`** | Feedback components | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/feedback_examples.py) |
| **`tree`, `carousel`** | Hierarchical and carousel display | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/tree_state.py) |
| **`number_formatter`** | Formats numeric input with parser/formatter, returns parsed value | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/number_formatter_examples.py) |

### Charts

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **`area_chart`, `bar_chart`, `line_chart`, `pie_chart`, `donut_chart`, `radar_chart`, `radial_bar_chart`, `scatter_chart`, `composite_chart`, `bubble_chart`, `funnel_chart`, `heatmap`, `treemap`, `sankey_chart`, `sparkline`, `bars_list`** | Recharts-powered charting components | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/charts_examples.py) |

### Maps & Scheduling

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **`map`, `MapMarker`, `MapControls`, `MapNavigation`, `MapDirectionsPanel`, `MapArc`, `MapGeoJSON`, `MapRoute`, `MapClusterLayer`** | MapLibre-based map components | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/map_examples.py) |
| **`schedule`, `resources_schedule`, `resources_day_view`, `resources_week_view`, `resources_month_view`, `agenda_view`** | Calendar/resource scheduling components | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/schedule_examples.py) / [Resources](https://github.com/jenreh/appkit/tree/main/app/pages/examples/resources_schedule_examples.py) |

### Typography & Markdown

| Component | Description | Documentation |
|-----------|-------------|---------------|
| **`text`, `title`, `code`, `mark`, `highlight`, `blockquote`, `list_`** | Typography primitives | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/typography_examples.py) |
| **`markdown_preview`** | Markdown renderer with Mermaid diagrams and math support | [Examples](https://github.com/jenreh/appkit/tree/main/app/pages/examples/markdown_preview_examples.py) |

### Common Props (Inherited by All Inputs)

All input components inherit ~40 common props from `MantineInputComponentBase`:

```python
# Input.Wrapper props
label = "Field Label"
description = "Helper text"
error = "Validation error"
required = True
with_asterisk = True  # Show red asterisk for required fields

# Visual variants
variant = "filled"  # "default" | "filled" | "unstyled"
size = "md"  # "xs" | "sm" | "md" | "lg" | "xl"
radius = "md"  # "xs" | "sm" | "md" | "lg" | "xl"

# State management
value = State.field_value
default_value = "Initial value"
placeholder = "Enter text..."
disabled = False

# Sections (icons, buttons)
left_section = rx.icon("search")
right_section = rx.button("Clear")
left_section_pointer_events = "none"  # Click-through

# Mantine style props
w = "100%"  # width
maw = "500px"  # max-width
m = "md"  # margin
p = "sm"  # padding

# Event handlers
on_change = State.handle_change
on_focus = State.handle_focus
on_blur = State.handle_blur
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

    def handle_phone(self, value: str) -> None:
        self.phone = value


def phone_input():
    # Use as an UNCONTROLLED component: default_value + on_change (not value)
    return mn.masked_input(
        label="Phone Number",
        mask="+1 (000) 000-0000",
        default_value="+1 (555) 123-4567",
        on_change=PhoneState.handle_phone,
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
