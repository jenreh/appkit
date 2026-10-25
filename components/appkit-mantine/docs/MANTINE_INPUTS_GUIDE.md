# Mantine Input Components - Complete Guide

**Comprehensive Reflex wrappers for Mantine UI Input components with advanced features including masked inputs.**

---

## 📚 Table of Contents

1. [Quick Start](#quick-start)
2. [Installation & Setup](#installation--setup)
3. [Basic Input Components](#basic-input-components)
4. [Masked Input (IMask)](#masked-input-imask)
5. [Common Patterns](#common-patterns)
6. [Props Reference](#props-reference)
7. [Event Handlers](#event-handlers)
8. [Styling](#styling)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### ⚠️ Critical: MantineProvider Required

**ALL Mantine components MUST be wrapped in `mantine_provider`!**

```python
from appkit_ui.components import mantine_provider, mantine_input

def my_page():
    return mantine_provider(
        # Your content here
        mantine_input(placeholder="Search..."),
        default_color_scheme="light",
    )
```

### Basic Example

```python
import reflex as rx
from appkit_ui.components import (
    mantine_provider,
    mantine_input,
    mantine_input_wrapper,
)

class FormState(rx.State):
    email: str = ""

def contact_form():
    return mantine_provider(
        mantine_input_wrapper(
            mantine_input(
                value=FormState.email,
                on_change=FormState.set_email,
                type="email",
            ),
            label="Email Address",
            description="We'll never share your email",
            required=True,
        ),
        default_color_scheme="light",
    )
```

---

## Installation & Setup

### Import Components

```python
# Basic inputs
from appkit_ui.components import (
    mantine_provider,        # Required wrapper
    mantine_input,           # Base input
    mantine_input_wrapper,   # Complete form field
    mantine_input_label,     # Label
    mantine_input_description, # Help text
    mantine_input_error,     # Error message
    mantine_input_clear_button, # Clear button
)

# Masked inputs
from appkit_ui.components import (
    mantine_imask_input,     # Phone, credit card, date formatting
)
```

### Dependencies

These are automatically installed by Reflex:


- `@mantine/core@9.7.3` - Mantine UI library
- `react-imask@7.6.1` - Input masking library

---

## Basic Input Components

### 1. Simple Input

```python
mantine_input(
    placeholder="Enter text...",
    on_change=State.set_value,
)
```

### 2. Complete Form Field (Input.Wrapper)

The most common pattern - includes label, description, and error handling:

```python
mantine_input_wrapper(
    mantine_input(
        value=State.email,
        on_change=State.set_email,
        type="email",
    ),
    label="Email",
    description="We'll never share your email",
    error=State.email_error,  # Show error message
    required=True,  # Adds asterisk and required attribute
)
```

### 3. Input with Icons/Sections

```python
# Search input with icon
mantine_input(
    placeholder="Search...",
    left_section=rx.icon("search", size=16),
    left_section_pointer_events="none",  # Icon not clickable
    on_change=State.set_query,
)

# Input with clear button
mantine_input(
    value=State.query,
    placeholder="Clearable input",
    right_section=rx.cond(
        State.query,
        mantine_input_clear_button(on_click=lambda: State.set_query("")),
        rx.fragment(),
    ),
    right_section_pointer_events="all",  # Button is clickable
    on_change=State.set_query,
)
```

### 4. Password Input with Visibility Toggle

```python
class PasswordState(rx.State):
    password: str = ""
    show_password: bool = False

    @rx.event
    def toggle_password(self):
        self.show_password = not self.show_password

mantine_input_wrapper(
    mantine_input(
        value=PasswordState.password,
        type=rx.cond(PasswordState.show_password, "text", "password"),
        on_change=PasswordState.set_password,
        right_section=rx.icon_button(
            rx.icon(
                rx.cond(PasswordState.show_password, "eye-off", "eye"),
                size=16,
            ),
            variant="ghost",
            on_click=PasswordState.toggle_password,
        ),
        right_section_pointer_events="all",
    ),
    label="Password",
    required=True,
)
```

### 5. Custom Layout

For more control, use individual components:

```python
rx.vstack(
    mantine_input_label("Field Name", required=True),
    mantine_input_description("Help text goes here"),
    mantine_input(
        value=State.value,
        on_change=State.set_value,
    ),
    rx.cond(
        State.error,
        mantine_input_error(State.error),
        rx.fragment(),
    ),
    spacing="2",
)
```

---

## Masked Input (IMask)

**For formatted inputs like phone numbers, credit cards, and dates.**

### ⚠️ Critical: Uncontrolled Component Pattern

**IMask components are UNCONTROLLED** - never use the `value` prop!

```python
# ❌ WRONG - Will prevent typing!
mantine_imask_input(
    mask="+1 (000) 000-0000",
    value=State.phone,  # ❌ DO NOT USE!
    on_accept=State.set_phone,
)

# ✅ CORRECT - Input accepts typing
mantine_imask_input(
    mask="+1 (000) 000-0000",
    on_accept=State.set_phone,  # ✅ Capture value via on_accept
)
```

### Phone Number Input

```python
class ContactState(rx.State):
    phone: str = ""

    @rx.event
    def set_phone(self, value: str) -> None:
        self.phone = value

# US format
mantine_imask_input(
    mask="+1 (000) 000-0000",
    placeholder="Your phone",
    left_section=rx.icon("phone", size=16),
    left_section_pointer_events="none",
    on_accept=ContactState.set_phone,
)
```

### Credit Card Input

```python
mantine_imask_input(
    mask="0000 0000 0000 0000",
    placeholder="Card number",
    left_section=rx.icon("credit-card", size=16),
    left_section_pointer_events="none",
    unmask=True,  # Returns "1234567890123456" without spaces
    on_accept=State.set_card_number,
)
```

### Date Input

```python
mantine_imask_input(
    mask="00/00/0000",
    placeholder="MM/DD/YYYY",
    left_section=rx.icon("calendar", size=16),
    left_section_pointer_events="none",
    on_accept=State.set_date,
)
```

### Initial Values

Use `default_value` (not `value`):

```python
mantine_imask_input(
    mask="+1 (000) 000-0000",
    default_value="+1 (555) 123-4567",  # ✅ Sets initial value
    on_accept=State.set_phone,
)
```

### Common Mask Patterns

```python
# Phone numbers
"+1 (000) 000-0000"        # US format
"+44 0000 000000"          # UK format
"+49 (000) 000-0000"       # Germany format

# Credit cards
"0000 0000 0000 0000"      # 16 digits with spaces
"0000-0000-0000-0000"      # 16 digits with dashes

# Dates
"00/00/0000"               # MM/DD/YYYY
"00-00-0000"               # DD-MM-YYYY
"0000-00-00"               # YYYY-MM-DD

# Postal codes
"00000"                    # US ZIP
"00000-0000"               # US ZIP+4
"A0A 0A0"                  # Canadian (A = letter)

# Time
"00:00:00"                 # HH:MM:SS
"00:00"                    # HH:MM

# Custom
"AAA-000"                  # Letters-Numbers
```

### Custom Pattern Definitions

```python
mantine_imask_input(
    mask="AAA-000",
    definitions={
        "A": r"[A-Z]",  # A = uppercase letter
        "0": r"[0-9]",  # 0 = digit
    },
    placeholder="ABC-123",
    on_accept=State.set_custom,
)
```

---

## Common Patterns

### Email Input

```python
mantine_input_wrapper(
    mantine_input(
        type="email",
        value=State.email,
        on_change=State.set_email,
        on_blur=State.validate_email,
        left_section=rx.icon("mail", size=16),
        left_section_pointer_events="none",
    ),
    label="Email Address",
    description="Enter your email",
    error=State.email_error,
    required=True,
)
```

### Search with Live Results

```python
class SearchState(rx.State):
    query: str = ""
    results: list[str] = []

    @rx.event
    async def search(self, query: str):
        self.query = query
        # Perform search...
        self.results = await fetch_results(query)

def search_box():
    return mantine_input(
        value=SearchState.query,
        placeholder="Search...",
        left_section=rx.icon("search", size=16),
        left_section_pointer_events="none",
        right_section=rx.cond(
            SearchState.query,
            mantine_input_clear_button(
                on_click=lambda: SearchState.set_query("")
            ),
            rx.fragment(),
        ),
        right_section_pointer_events="all",
        on_change=SearchState.search,
    )
```

### Validation on Blur

```python
class FormState(rx.State):
    username: str = ""
    error: str = ""

    @rx.event
    async def validate_username(self):
        if len(self.username) < 3:
            self.error = "Username must be at least 3 characters"
        elif not self.username.isalnum():
            self.error = "Username must be alphanumeric"
        else:
            self.error = ""

mantine_input_wrapper(
    mantine_input(
        value=FormState.username,
        on_change=FormState.set_username,
        on_blur=FormState.validate_username,
    ),
    label="Username",
    error=FormState.error,
    required=True,
)
```

---

## Props Reference

### Input Component Props

#### Visual Variants

```python
variant="default"   # Outlined (default)
variant="filled"    # Filled background
variant="unstyled"  # No styles
```

#### Sizes

```python
size="xs"   # Extra small
size="sm"   # Small
size="md"   # Medium (default)
size="lg"   # Large
size="xl"   # Extra large
```

#### Border Radius

```python
radius="xs"   # Sharp corners
radius="sm"   # Slightly rounded
radius="md"   # Medium rounded (default)
radius="lg"   # Very rounded
radius="xl"   # Pill-shaped
```

#### States

```python
disabled=True   # Disabled state
error=True      # Error state (red border)
required=True   # Required attribute + asterisk
```

#### Sections (Icons/Buttons/Custom Content)

```python
# Any Reflex component can be used
left_section=rx.icon("search", size=16)
right_section=rx.button("Go")

# Control width
left_section_width=40
right_section_width="50px"

# Pointer events (click handling)
left_section_pointer_events="none"   # Decorative (clicks pass through)
right_section_pointer_events="all"   # Interactive (receives clicks)
```

### InputWrapper Component Props

```python
label="Field Label"              # Label text
description="Help text"          # Description
error="Error message"            # Error message
required=True                    # Shows asterisk + required attr
with_asterisk=True              # Shows asterisk without required
size="md"                        # Component size
input_wrapper_order=[            # Custom element order
    "label",
    "description",
    "input",
    "error"
]
```

### IMask Component Props

#### Mask Configuration

```python
mask="+1 (000) 000-0000"        # Mask pattern (required)
lazy=True                        # Show mask only when typing (default)
placeholder_char="_"             # Placeholder character
unmask=False                     # Return unmasked value
overwrite=False                  # Allow overwriting
autofix=False                    # Auto-fix on blur
eager=False                      # Eager mask display
definitions={"A": r"[A-Z]"}     # Custom pattern definitions
```

---

## Event Handlers

### Standard Input Events

```python
on_change=State.set_value      # Value changes (receives str)
on_focus=State.handle_focus    # Input focused (no args)
on_blur=State.handle_blur      # Input blurred (no args)
on_key_down=State.handle_key   # Key pressed (receives key str)
on_key_up=State.handle_key     # Key released (receives key str)
```

### IMask Events

```python
on_accept=State.set_phone      # Mask accepts input (receives str) - USE THIS!
on_complete=State.validate     # Mask completely filled (receives str)
```

### Event Handler Signatures

```python
class State(rx.State):
    value: str = ""
    focused: bool = False
    last_key: str = ""

    @rx.event
    def set_value(self, value: str) -> None:
        """on_change handler - receives value as string."""
        self.value = value

    @rx.event
    def handle_focus(self) -> None:
        """on_focus/on_blur handler - no arguments."""
        self.focused = True

    @rx.event
    def handle_key(self, key: str) -> None:
        """on_key_down/on_key_up handler - receives key as string."""
        self.last_key = key
```

---

## Styling

### Using Reflex's Built-in Styling

```python
mantine_input(
    placeholder="Styled input",
    variant="filled",
    size="lg",
    radius="xl",
    width="100%",
    max_width="400px",
)
```

### Combining with Reflex Layout

```python
rx.vstack(
    mantine_input_wrapper(
        mantine_input(placeholder="First name"),
        label="First Name",
    ),
    mantine_input_wrapper(
        mantine_input(placeholder="Last name"),
        label="Last Name",
    ),
    spacing="4",
    width="100%",
    max_width="400px",
)
```

### Responsive Sizing

```python
mantine_input(
    size=["sm", "md", "lg"],  # Mobile, tablet, desktop
    width=["100%", "100%", "400px"],
)
```

---

## Troubleshooting

### Issue: Mantine components don't render

**Solution:** Wrap your page in `mantine_provider`:

```python
def my_page():
    return mantine_provider(
        # Your content
        default_color_scheme="light",
    )
```

### Issue: IMask input doesn't accept typing

**Problem:** Using `value` prop on IMask component.

**Solution:** Remove `value` prop, use `on_accept` instead:

```python
# ❌ Wrong
mantine_imask_input(value=State.phone, ...)

# ✅ Correct
mantine_imask_input(on_accept=State.set_phone, ...)
```

### Issue: Event handler type mismatch

**Problem:** Wrong event spec for handler.

**Solution:** Use proper state setter:

```python
# ✅ Correct
class State(rx.State):
    value: str = ""

mantine_input(
    value=State.value,
    on_change=State.set_value,  # Auto-generated setter
)
```

### Issue: Clear button doesn't work

**Problem:** Missing `right_section_pointer_events`.

**Solution:** Set pointer events to `"all"`:

```python
mantine_input(
    right_section=mantine_input_clear_button(...),
    right_section_pointer_events="all",  # Required for clicks!
)
```

### Issue: Icon interferes with input clicks

**Problem:** Icon captures clicks meant for input.

**Solution:** Set `left_section_pointer_events="none"`:

```python
mantine_input(
    left_section=rx.icon("search"),
    left_section_pointer_events="none",  # Clicks pass through
)
```

---

## Complete Examples

### Contact Form

```python
import reflex as rx
from appkit_ui.components import (
    mantine_provider,
    mantine_input_wrapper,
    mantine_input,
    mantine_imask_input,
)

class ContactFormState(rx.State):
    name: str = ""
    email: str = ""
    phone: str = ""
    message: str = ""

    name_error: str = ""
    email_error: str = ""

    @rx.event
    async def validate_name(self):
        if len(self.name) < 2:
            self.name_error = "Name must be at least 2 characters"
        else:
            self.name_error = ""

    @rx.event
    async def validate_email(self):
        if not self.email or "@" not in self.email:
            self.email_error = "Invalid email address"
        else:
            self.email_error = ""

    @rx.event
    async def submit_form(self):
        await self.validate_name()
        await self.validate_email()

        if not self.name_error and not self.email_error:
            # Submit form
            yield rx.toast.success("Form submitted!", position="top-right")

def contact_form():
    return mantine_provider(
        rx.vstack(
            rx.heading("Contact Us", size="6"),

            # Name field
            mantine_input_wrapper(
                mantine_input(
                    value=ContactFormState.name,
                    on_change=ContactFormState.set_name,
                    on_blur=ContactFormState.validate_name,
                    left_section=rx.icon("user", size=16),
                    left_section_pointer_events="none",
                ),
                label="Full Name",
                error=ContactFormState.name_error,
                required=True,
            ),

            # Email field
            mantine_input_wrapper(
                mantine_input(
                    value=ContactFormState.email,
                    on_change=ContactFormState.set_email,
                    on_blur=ContactFormState.validate_email,
                    type="email",
                    left_section=rx.icon("mail", size=16),
                    left_section_pointer_events="none",
                ),
                label="Email",
                error=ContactFormState.email_error,
                required=True,
            ),

            # Phone field (masked)
            mantine_input_wrapper(
                mantine_imask_input(
                    mask="+1 (000) 000-0000",
                    on_accept=ContactFormState.set_phone,
                    left_section=rx.icon("phone", size=16),
                    left_section_pointer_events="none",
                ),
                label="Phone",
                description="US phone number",
            ),

            # Message field
            mantine_input_wrapper(
                mantine_input(
                    component="textarea",
                    value=ContactFormState.message,
                    on_change=ContactFormState.set_message,
                    rows="4",
                ),
                label="Message",
                description="Tell us how we can help",
            ),

            # Submit button
            rx.button(
                "Submit",
                on_click=ContactFormState.submit_form,
                size="3",
            ),

            spacing="4",
            width="100%",
            max_width="500px",
        ),
        default_color_scheme="light",
    )
```

---

## Additional Resources
<https://mantine.dev/core/input/>
- **Mantine Documentation:*<https://imask.js.org/guide.html>ut/>
- **IMask Documentation:** <<https://reflex.dev/docs/>de.html>
- **Reflex Documentation:** <https://reflex.dev/docs/>

---

## Summary

### Key Takeaways

1. **Always wrap in MantineProvider** - Required for all Mantine components
2. **Use `on_change` for regular inputs** - Receives value as string
3. **Use `on_accept` for IMask inputs** - Never use `value` prop
4. **Use `Input.Wrapper` for complete form fields** - Label, description, error
5. **Set `pointer_events` for sections** - `"none"` for icons, `"all"` for buttons
6. **Validate on `on_blur`** - Better UX than on every keystroke
7. **Use `default_value` for IMask** - Not `value` prop

### Quick Reference

```python
# Basic input
mantine_input(placeholder="Text", on_change=State.set_value)

# Complete field
mantine_input_wrapper(
    mantine_input(...),
    label="Label",
    error=State.error,
    required=True,
)

# Masked input
mantine_imask_input(
    mask="+1 (000) 000-0000",
    on_accept=State.set_phone,  # Not on_change!
)

# With sections
mantine_input(
    left_section=rx.icon("search"),
    left_section_pointer_events="none",
)
```

Happy coding! 🎉
