# Mantine Textarea Component - Complete Guide

**Comprehensive Reflex wrapper for Mantine UI Textarea component with autosize, validation, and all Input features.**

---

## 📚 Quick Start

### ⚠️ Critical: MantineProvider Required

**ALL Mantine components MUST be wrapped in `mantine_provider`!**

```python
from appkit_ui.components import mantine_provider, mantine_textarea

def my_page():
    return mantine_provider(
        mantine_textarea(
            placeholder="Enter your comment...",
            label="Comment",
        ),
        default_color_scheme="light",
    )
```

### Basic Example

```python
import reflex as rx
from appkit_ui.components import (
    mantine_provider,
    mantine_textarea,
)

class FormState(rx.State):
    comment: str = ""

def comment_form():
    return mantine_provider(
        mantine_textarea(
            value=FormState.comment,
            on_change=FormState.set_comment,
            label="Your Comment",
            description="Share your thoughts",
            placeholder="Type here...",
            required=True,
        ),
        default_color_scheme="light",
    )
```

---

## 📦 Installation & Import

### Import

```python
from appkit_ui.components import (
    mantine_provider,    # Required wrapper
    mantine_textarea,    # Textarea component
)
```

### Dependencies

Automatically installed by Reflex:

- `@mantine/core@8.3.14` - Mantine UI library
- `react-textarea-autosize` - For autosize feature (used internally by Mantine)

---

## 🎨 Features

### 1. Basic Textarea

```python
mantine_textarea(
    placeholder="Enter text...",
    on_change=State.set_value,
)
```

### 2. With Label, Description, and Error

```python
mantine_textarea(
    label="Feedback",
    description="Help us improve our service",
    placeholder="Your feedback...",
    error=State.feedback_error,
    required=True,
    value=State.feedback,
    on_change=State.set_feedback,
)
```

### 3. Autosize (Growing Textarea)

The autosize feature automatically adjusts the textarea height as content grows:

```python
# Grows indefinitely
mantine_textarea(
    label="Bio",
    placeholder="Tell us about yourself...",
    autosize=True,
    min_rows=3,
    on_change=State.set_bio,
)

# Limited growth
mantine_textarea(
    label="Comment",
    placeholder="Your comment...",
    autosize=True,
    min_rows=2,
    max_rows=6,  # Stops growing at 6 rows, then scrolls
    on_change=State.set_comment,
)
```

### 4. Manual Resize Control

Enable user to manually resize the textarea:

```python
# No resize (default)
mantine_textarea(
    placeholder="Fixed size",
    resize="none",
    rows=4,
)

# Vertical resize only
mantine_textarea(
    placeholder="Resize vertically",
    resize="vertical",
    rows=4,
)

# Both directions
mantine_textarea(
    placeholder="Resize any direction",
    resize="both",
    rows=4,
)
```

### 5. Character Count

Track character count for maximum length enforcement:

```python
class TextState(rx.State):
    bio: str = ""
    char_count: int = 0

    @rx.event
    def set_bio(self, value: str) -> None:
        self.bio = value
        self.char_count = len(value)

mantine_textarea(
    label="Bio",
    description=f"Characters: {TextState.char_count}/500",
    placeholder="Tell us about yourself...",
    value=TextState.bio,
    max_length=500,
    on_change=TextState.set_bio,
)
```

---

## 🎨 Variants

Textarea supports three visual variants:

```python
# Default (outlined)
mantine_textarea(
    placeholder="Default variant",
    variant="default",
)

# Filled (background)
mantine_textarea(
    placeholder="Filled variant",
    variant="filled",
)

# Unstyled (no styles)
mantine_textarea(
    placeholder="Unstyled variant",
    variant="unstyled",
)
```

---

## 📏 Sizes

Five predefined sizes from `xs` to `xl`:

```python
mantine_textarea(placeholder="Extra small", size="xs")
mantine_textarea(placeholder="Small", size="sm")
mantine_textarea(placeholder="Medium", size="md")  # default
mantine_textarea(placeholder="Large", size="lg")
mantine_textarea(placeholder="Extra large", size="xl")
```

---

## 🔵 Border Radius

Control the border radius:

```python
mantine_textarea(placeholder="Sharp", radius="xs")
mantine_textarea(placeholder="Rounded", radius="md")
mantine_textarea(placeholder="Very rounded", radius="xl")
```

---

## 📝 Complete Examples

### Form with Validation

```python
class FeedbackState(rx.State):
    feedback: str = ""
    feedback_error: str = ""

    @rx.event
    async def validate_feedback(self):
        if len(self.feedback) < 10:
            self.feedback_error = "Feedback must be at least 10 characters"
        else:
            self.feedback_error = ""

    @rx.event
    async def submit(self):
        await self.validate_feedback()
        if not self.feedback_error:
            # Submit form
            yield rx.toast.success("Submitted!", position="top-right")

def feedback_form():
    return mantine_textarea(
        label="Feedback",
        description="Minimum 10 characters required",
        placeholder="Tell us what you think...",
        value=FeedbackState.feedback,
        error=FeedbackState.feedback_error,
        required=True,
        autosize=True,
        min_rows=3,
        max_rows=8,
        on_change=FeedbackState.set_feedback,
        on_blur=FeedbackState.validate_feedback,
    )
```

### Bio with Character Limit

```python
class ProfileState(rx.State):
    bio: str = ""
    char_count: int = 0
    word_count: int = 0
    bio_error: str = ""

    @rx.event
    def set_bio(self, value: str) -> None:
        self.bio = value
        self.char_count = len(value)
        self.word_count = len(value.split()) if value else 0

    @rx.event
    async def validate_bio(self):
        if len(self.bio) > 500:
            self.bio_error = "Bio must not exceed 500 characters"
        else:
            self.bio_error = ""

def bio_field():
    return mantine_textarea(
        label="Bio",
        description=f"{ProfileState.char_count}/500 chars, {ProfileState.word_count} words",
        placeholder="Tell us about yourself...",
        value=ProfileState.bio,
        error=ProfileState.bio_error,
        max_length=500,
        autosize=True,
        min_rows=4,
        max_rows=10,
        on_change=ProfileState.set_bio,
        on_blur=ProfileState.validate_bio,
        variant="filled",
    )
```

### Multi-Field Form

```python
class ContactState(rx.State):
    message: str = ""
    comments: str = ""
    feedback: str = ""

    @rx.event
    async def submit_form(self):
        # Validate and submit
        yield rx.toast.success("Form submitted!", position="top-right")

def contact_form():
    return mantine_provider(
        mn.stack(
            rx.heading("Contact Us", size="6"),

            mantine_textarea(
                label="Message",
                description="Required - Tell us how we can help",
                placeholder="Your message...",
                value=ContactState.message,
                required=True,
                autosize=True,
                min_rows=3,
                max_rows=8,
                on_change=ContactState.set_message,
                variant="filled",
            ),

            mantine_textarea(
                label="Additional Comments",
                description="Optional",
                placeholder="Any other details?",
                value=ContactState.comments,
                autosize=True,
                min_rows=2,
                max_rows=5,
                on_change=ContactState.set_comments,
                variant="filled",
            ),

            mn.button(
                "Submit",
                on_click=ContactState.submit_form,
                size="md",
            ),

            gap="sm",
            w="100%",
            maw="600px",
        ),
        default_color_scheme="light",
    )
```

---

## 🎯 Props Reference

### Value & Placeholder

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `value` | `str` | - | Controlled value |
| `default_value` | `str` | - | Uncontrolled default value |
| `placeholder` | `str` | - | Placeholder text |

### Visual Variants

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `variant` | `"default" \| "filled" \| "unstyled"` | `"default"` | Visual variant |
| `size` | `"xs" \| "sm" \| "md" \| "lg" \| "xl"` | `"md"` | Component size |
| `radius` | `"xs" \| "sm" \| "md" \| "lg" \| "xl"` | `"md"` | Border radius |

### States

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `disabled` | `bool` | `False` | Disabled state |
| `required` | `bool` | `False` | Required field |
| `error` | `bool \| str` | - | Error state or message |

### Label & Description

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `label` | `str` | - | Label text |
| `description` | `str` | - | Description text |
| `with_asterisk` | `bool` | `False` | Show asterisk without required |

### HTML Attributes

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `name` | `str` | - | Input name attribute |
| `id` | `str` | - | Input id attribute |
| `rows` | `int` | - | Number of visible lines |
| `cols` | `int` | - | Visible width |
| `max_length` | `int` | - | Maximum character length |
| `min_length` | `int` | - | Minimum character length |
| `auto_complete` | `str` | - | Autocomplete attribute |
| `aria_label` | `str` | - | Accessibility label |
| `wrap` | `"soft" \| "hard" \| "off"` | - | Text wrapping behavior |

### Autosize Feature

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `autosize` | `bool` | `False` | Enable automatic height |
| `min_rows` | `int` | - | Minimum rows (with autosize) |
| `max_rows` | `int` | - | Maximum rows (with autosize) |

### Resize Control

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `resize` | `"none" \| "vertical" \| "both" \| "horizontal"` | `"none"` | CSS resize property |

---

## 🔄 Event Handlers

### Available Events

```python
on_change=State.set_value      # Value changes (receives str)
on_focus=State.handle_focus    # Textarea focused (no args)
on_blur=State.handle_blur      # Textarea blurred (no args)
on_key_down=State.handle_key   # Key pressed (receives key str)
on_key_up=State.handle_key     # Key released (receives key str)
on_input=State.handle_input    # Input event (receives str)
```

### Event Handler Signatures

```python
class State(rx.State):
    value: str = ""
    focused: bool = False

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
        """on_key_down/on_key_up handler - receives key."""
        if key == "Enter":
            # Handle enter key
            pass
```

---

## 🎨 Styling

### Using Reflex's Built-in Styling

```python
mantine_textarea(
    placeholder="Styled textarea",
    variant="filled",
    size="lg",
    radius="xl",
    width="100%",
    max_width="600px",
)
```

### Responsive Design

```python
mantine_textarea(
    size=["sm", "md", "lg"],  # Mobile, tablet, desktop
    width=["100%", "100%", "600px"],
)
```

---

## 🔧 Troubleshooting

### Issue: Mantine components don't render

**Solution:** Wrap your page in `mantine_provider`:

```python
def my_page():
    return mantine_provider(
        # Your content
        default_color_scheme="light",
    )
```

### Issue: Autosize doesn't work

**Problem:** Missing `autosize=True` prop.

**Solution:** Enable autosize explicitly:

```python
mantine_textarea(
    autosize=True,
    min_rows=3,
    max_rows=10,
)
```

### Issue: Can't resize textarea manually

**Problem:** Default `resize="none"`.

**Solution:** Set resize to `"vertical"` or `"both"`:

```python
mantine_textarea(
    resize="vertical",
    rows=4,
)
```

### Issue: Character limit not enforced

**Problem:** `max_length` is just a hint, not strict validation.

**Solution:** Implement validation in state:

```python
class State(rx.State):
    text: str = ""

    @rx.event
    def set_text(self, value: str) -> None:
        if len(value) <= 500:  # Enforce limit
            self.text = value

mantine_textarea(
    value=State.text,
    max_length=500,
    on_change=State.set_text,
)
```

---

## 📚 Common Patterns

### Pattern 1: Validation on Blur

```python
class State(rx.State):
    message: str = ""
    error: str = ""

    @rx.event
    async def validate(self):
        if len(self.message) < 10:
            self.error = "Message too short"
        else:
            self.error = ""

mantine_textarea(
    value=State.message,
    error=State.error,
    on_change=State.set_message,
    on_blur=State.validate,
)
```

### Pattern 2: Character Counter

```python
class State(rx.State):
    text: str = ""

    @rx.var
    def char_count(self) -> str:
        return f"{len(self.text)}/500"

mantine_textarea(
    description=State.char_count,
    max_length=500,
    value=State.text,
    on_change=State.set_text,
)
```

### Pattern 3: Submit on Ctrl+Enter

```python
class State(rx.State):
    message: str = ""

    @rx.event
    async def handle_key(self, key: str):
        # Note: Detecting Ctrl needs additional event data
        # This is a simplified example
        if key == "Enter":
            await self.submit()

mantine_textarea(
    value=State.message,
    on_key_down=State.handle_key,
)
```

---

## 📖 Comparison: Textarea vs Input

| Feature | Input | Textarea |
|---------|-------|----------|
| Multi-line | ❌ No | ✅ Yes |
| Autosize | ❌ No | ✅ Yes |
| Resize | ❌ No | ✅ Yes (vertical/both) |
| Rows/Cols | ❌ No | ✅ Yes |
| Use Case | Single-line text | Multi-line text |

**When to use Textarea:**

- Comments, feedback, descriptions
- Long-form text entry
- When you need more than one line

**When to use Input:**

- Names, emails, phone numbers
- Single-line values
- Masked inputs (with IMask)

---

## 🎓 Best Practices

1. **Use autosize for better UX** - Users see all their content without scrolling
2. **Set min_rows and max_rows** - Prevent textarea from being too small or too large
3. **Validate on blur** - Better UX than validating on every keystroke
4. **Show character counts** - Help users stay within limits
5. **Use descriptive labels** - Make forms accessible
6. **Handle long text** - Consider max_rows to prevent excessive page growth
7. **Provide clear error messages** - Help users fix validation issues

---

## 📚 Additional Resources

- **Mantine Textarea Documentation:** <https://mantine.dev/core/textarea/>
- **Mantine Input Documentation:** <https://mantine.dev/core/input/>
- **Reflex Documentation:** <https://reflex.dev/docs/>

---

## Summary

### Key Takeaways

1. ✅ **Always wrap in MantineProvider** - Required for all Mantine components
2. ✅ **Use autosize for better UX** - Textarea grows with content
3. ✅ **Set min_rows and max_rows** - Control growth limits
4. ✅ **Use on_blur for validation** - Better UX than on every keystroke
5. ✅ **Inherit all Input features** - Label, description, error, variants, sizes

### Quick Reference

```python
# Basic textarea
mantine_textarea(placeholder="Text", on_change=State.set_value)

# With label and error
mantine_textarea(
    label="Feedback",
    error=State.error,
    required=True,
)

# Autosize
mantine_textarea(
    autosize=True,
    min_rows=3,
    max_rows=8,
)

# Manual resize
mantine_textarea(
    resize="vertical",
    rows=4,
)
```

Happy coding! 🎉
