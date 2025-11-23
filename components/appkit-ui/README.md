# appkit-ui

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Shared UI components and layouts for AppKit applications.**

appkit-ui provides a collection of reusable UI components, layouts, and styling utilities designed to create consistent, professional interfaces across AppKit applications. It includes responsive page templates, navigation components, form helpers, and common UI patterns built on Reflex and Mantine.

---

## ✨ Features

- **Layout Components** - Responsive page templates and navigation headers
- **Form Helpers** - Pre-built form inputs with validation and styling
- **Dialog Components** - Confirmation dialogs and modal interfaces
- **Rich Text Editor** - Full-featured WYSIWYG editor based on SunEditor
- **Collapsible Sections** - Expandable/collapsible content areas
- **Global State Management** - Shared state for loading indicators and UI feedback
- **Styling Utilities** - Consistent themes, colors, and CSS utilities
- **Responsive Design** - Mobile-first components that work across all screen sizes

---

## 🚀 Installation

### As Part of AppKit Workspace

If you're using the full AppKit workspace:

```bash
git clone https://github.com/jenreh/appkit.git
cd appkit
uv sync
```

### Standalone Installation

Install from PyPI:

```bash
pip install appkit-ui
```

Or with uv:

```bash
uv add appkit-ui
```

### Dependencies

- `appkit-commons` (shared utilities)
- `reflex>=0.8.12` (UI framework)

---

## 🏁 Quick Start

### Basic Layout

Create a responsive page layout with header:

```python
import reflex as rx
import appkit_ui as ui

def my_page():
    return rx.vstack(
        ui.header("My Application"),
        rx.container(
            rx.text("Welcome to my app!"),
            max_width="800px",
            padding="2em"
        ),
        spacing="0",
        min_height="100vh"
    )
```

### Using Form Components

Add styled form inputs:

```python
from appkit_ui.components.form_inputs import inline_form_field

def contact_form():
    return rx.form(
        inline_form_field(
            icon="user",
            label="Name",
            placeholder="Enter your name",
            required=True
        ),
        inline_form_field(
            icon="mail",
            label="Email",
            type="email",
            placeholder="Enter your email"
        ),
        rx.button("Submit", type="submit")
    )
```

### Rich Text Editor

Add a WYSIWYG editor to your page:

```python
from appkit_ui.components import editor

def blog_editor():
    return editor(
        placeholder="Write your blog post...",
        button_list=editor.EditorButtonList.COMPLEX,
        height="400px"
    )
```

---

## 📖 Usage

### Layout Components

#### Header

Create a fixed header with responsive design:

```python
from appkit_ui.components.header import header

# Basic header
header("Application Title")

# Indented header (for sidebar layouts)
header("Dashboard", indent=True)
```

#### Styles and Themes

Apply consistent styling:

```python
import appkit_ui.styles as styles

def styled_page():
    return rx.box(
        rx.text("Content"),
        **styles.splash_container  # Gradient background
    )
```

### Form Components

#### Inline Form Fields

Create labeled form inputs with icons:

```python
from appkit_ui.components.form_inputs import inline_form_field

# Text input
inline_form_field(
    icon="user",
    label="Username",
    placeholder="Enter username",
    min_length=3,
    max_length=50
)

# Email input
inline_form_field(
    icon="mail",
    label="Email",
    type="email",
    required=True
)

# Password input
inline_form_field(
    icon="lock",
    label="Password",
    type="password",
    hint="Must be at least 8 characters"
)
```

#### Hidden Fields

Add hidden form data:

```python
from appkit_ui.components.form_inputs import hidden_field

hidden_field(name="csrf_token", value="abc123")
```

### Dialog Components

#### Delete Confirmation Dialog

Create a confirmation dialog for destructive actions:

```python
from appkit_ui.components.dialogs import delete_dialog

def user_management():
    return rx.vstack(
        delete_dialog(
            title="Delete User",
            content="user@example.com",
            on_click=lambda: print("User deleted")
        ),
        # Other user management UI
    )
```

### Editor Component

#### Rich Text Editor

Configure the editor with different button sets:

```python
from appkit_ui.components import editor

# Basic editor
editor(placeholder="Enter text...")

# Full-featured editor
editor(
    button_list=editor.EditorButtonList.COMPLEX,
    height="500px",
    placeholder="Write your content...",
    on_change=lambda value: print(f"Content: {value}")
)
```

#### Editor Options

Customize editor behavior:

```python
from appkit_ui.components.editor import EditorOptions

custom_options = EditorOptions(
    height="400px",
    placeholder="Custom placeholder...",
    button_list=[
        ["bold", "italic"],
        ["link", "image"],
        ["undo", "redo"]
    ]
)

editor(options=custom_options)
```

### Collapsible Components

#### Collapsible Sections

Create expandable content areas:

```python
from appkit_ui.components import collabsible

def settings_page():
    return rx.vstack(
        collabsible(
            rx.text("Account settings content..."),
            title="Account Settings",
            info_text="Configure your account",
            expanded=True
        ),
        collabsible(
            rx.text("Notification settings content..."),
            title="Notifications",
            info_text="Manage email preferences"
        )
    )
```

### Global State

#### Loading State

Manage loading indicators across your app:

```python
from appkit_ui.global_states import LoadingState

class MyState(LoadingState):
    def load_data(self):
        self.set_is_loading(True)
        # Simulate async operation
        await asyncio.sleep(2)
        self.set_is_loading(False)

def loading_component():
    return rx.cond(
        LoadingState.is_loading,
        rx.text(LoadingState.is_loading_message),
        rx.text("Content loaded")
    )
```

---

## 🔧 Configuration

### Editor Configuration

Customize the rich text editor:

```python
from appkit_ui.components.editor import EditorOptions

options = EditorOptions(
    mode="classic",  # or "inline", "balloon"
    height="300px",
    min_height="200px",
    max_height="600px",
    placeholder="Start writing...",
    button_list=editor.EditorButtonList.FORMATTING,
    font_size: ["8px", "10px", "12px", "14px", "16px", "18px", "20px"],
    color_list: ["#ff0000", "#00ff00", "#0000ff"],
    # Additional SunEditor options...
)
```

### Styling Customization

Override default styles:

```python
import appkit_ui.styles as styles

# Custom dialog styles
custom_dialog_styles = {
    **styles.dialog_styles,
    "border_radius": "15px",
    "box_shadow": "0 10px 25px rgba(0,0,0,0.1)"
}
```

---

## 📋 API Reference

### Component API

#### Layout API

- `header()` - Fixed page header with responsive design

#### Form API

- `inline_form_field()` - Labeled form input with icon and validation
- `hidden_field()` - Hidden form input field

#### Dialog API

- `delete_dialog()` - Confirmation dialog for delete operations

#### Editor API

- `editor()` - Rich text WYSIWYG editor
- `EditorButtonList` - Predefined button configurations (BASIC, FORMATTING, COMPLEX)
- `EditorOptions` - Editor configuration options

#### Utility API

- `collabsible()` - Expandable/collapsible content sections

#### State API

- `LoadingState` - Global loading state with message support

#### Style API

- `splash_container` - Gradient background styles
- `dialog_styles` - Dialog component styling
- `label_styles` - Form label styling

---

## 🔒 Security

> [!IMPORTANT]
> Form components include basic client-side validation, but always implement server-side validation for security.

- Input sanitization for editor content
- CSRF protection support through hidden fields
- Secure handling of form data

---

## 🤝 Integration Examples

### With AppKit Components

Combine with other AppKit packages:

```python
import reflex as rx
import appkit_ui as ui
import appkit_mantine as mn
import appkit_user as user

def dashboard():
    return rx.vstack(
        ui.header("Dashboard", indent=True),
        rx.hstack(
            # Sidebar navigation
            mn.sidebar(),
            # Main content
            rx.container(
                ui.collabsible(
                    mn.data_table(),  # From appkit-mantine
                    title="User Data",
                    expanded=True
                ),
                max_width="1200px"
            ),
            flex_grow="1"
        ),
        min_height="100vh"
    )
```

### Custom Form with Validation

Create forms with integrated validation:

```python
from appkit_ui.components.form_inputs import inline_form_field

def registration_form():
    return rx.form(
        inline_form_field(
            icon="user",
            label="Username",
            name="username",
            min_length=3,
            max_length=20,
            pattern=r"^[a-zA-Z0-9_]+$",
            required=True
        ),
        inline_form_field(
            icon="mail",
            label="Email",
            name="email",
            type="email",
            required=True
        ),
        inline_form_field(
            icon="lock",
            label="Password",
            name="password",
            type="password",
            min_length=8,
            hint="At least 8 characters",
            required=True
        ),
        rx.button("Register", type="submit")
    )
```

### Editor Integration

Use the editor in content management:

```python
from appkit_ui.components import editor

class BlogState(rx.State):
    content: str = ""

    def save_post(self):
        # Save self.content to database
        pass

def blog_editor_page():
    return rx.vstack(
        ui.header("New Blog Post"),
        editor(
            value=BlogState.content,
            on_change=BlogState.set_content,
            button_list=editor.EditorButtonList.COMPLEX,
            height="600px",
            placeholder="Write your blog post..."
        ),
        rx.button("Save", on_click=BlogState.save_post),
        spacing="4",
        padding="2em"
    )
```

---

## 📚 Related Components

- **[appkit-mantine](./../appkit-mantine)** - Mantine UI components used throughout appkit-ui
- **[appkit-user](./../appkit-user)** - User authentication components
- **[appkit-commons](./../appkit-commons)** - Shared utilities and configuration
- **[appkit-assistant](./../appkit-assistant)** - AI assistant with UI components
