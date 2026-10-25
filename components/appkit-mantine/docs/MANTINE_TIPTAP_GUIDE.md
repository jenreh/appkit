# Mantine RichTextEditor (Tiptap) Guide

Comprehensive guide for using the Mantine RichTextEditor component in Reflex applications.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Component Variants](#component-variants)
- [Basic Usage](#basic-usage)
- [Controlled Mode](#controlled-mode)
- [Custom Toolbar](#custom-toolbar)
- [Available Controls](#available-controls)
- [Extensions](#extensions)
- [Styling and Theming](#styling-and-theming)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Installation

The RichTextEditor component is included in the `appkit-mantine` package. All required NPM dependencies are automatically installed when you use the component.

### NPM Dependencies

The component automatically installs:

- `@mantine/tiptap@9.7.3` - Mantine's Tiptap integration
- `@tiptap/react@^2.10.4` - React bindings for Tiptap
- `@tiptap/pm@^2.10.4` - ProseMirror core
- `@tiptap/extension-link@^2.10.4` - Link extension
- `@tiptap/starter-kit@^2.10.4` - Essential extensions bundle

### Optional Extensions

For additional functionality, these extensions are also supported (installed automatically when needed):

- `@tiptap/extension-highlight` - Text highlighting
- `@tiptap/extension-text-align` - Text alignment
- `@tiptap/extension-color` - Text color
- `@tiptap/extension-text-style` - Text styling (required for color)
- `@tiptap/extension-subscript` - Subscript text
- `@tiptap/extension-superscript` - Superscript text
- `@tiptap/extension-placeholder` - Placeholder text
- `@tiptap/extension-task-list` - Task lists
- `@tiptap/extension-task-item` - Task list items

---

## Quick Start

The fastest way to get started is using the `simple_rich_text_editor` component:

```python
import reflex as rx
import appkit_mantine as mn


class EditorState(rx.State):
    content: str = "<p>Hello World!</p>"

    def handle_update(self, html: str) -> None:
        self.content = html


def index() -> rx.Component:
    return rx.container(
        mn.simple_rich_text_editor(
            content=EditorState.content,
            on_update=EditorState.handle_update,
            placeholder="Start typing...",
        )
    )
```

---

## Component Variants

The library provides three ways to use the RichTextEditor:

### 1. SimpleRichTextEditor (Recommended for Quick Setup)

Pre-configured editor with a full-featured toolbar. Best for most use cases.

```python
mn.simple_rich_text_editor(
    content=State.content,
    on_update=State.handle_update,
    placeholder="Start typing...",
    sticky_toolbar=True,
    sticky_offset="0px",
)
```

**Props:**

- `content` - Initial HTML content
- `on_update` - Callback when content changes
- `editable` - Whether editor is editable (default: True)
- `placeholder` - Placeholder text
- `sticky_toolbar` - Make toolbar sticky on scroll
- `sticky_offset` - Top offset for sticky toolbar

### 2. MemoizedRichTextEditor (For Custom Toolbars)

Build your own toolbar by composing individual controls.

```python
mn.memoized_rich_text_editor(
    mn.rich_text_editor_toolbar(
        mn.rich_text_editor_controls_group(
            mn.rich_text_editor_bold(),
            mn.rich_text_editor_italic(),
        ),
    ),
    mn.rich_text_editor_content(),
    content=State.content,
    on_update=State.handle_update,
)
```

**Props:**

- `content` - Initial HTML content
- `on_update` - Callback when content changes
- `editable` - Whether editor is editable
- `placeholder` - Placeholder text
- `custom_extensions` - Additional Tiptap extensions
- `editor_options` - Advanced useEditor options
- `with_typography_styles` - Apply typography styles
- `variant` - Visual variant ('default' or 'subtle')

### 3. RichTextEditor (Advanced - Manual Editor Management)

Direct access to Mantine's RichTextEditor. Requires manually managing the Tiptap `useEditor` hook (advanced use only).

---

## Basic Usage

### Simple Editor with State

```python
import reflex as rx
import appkit_mantine as mn


class SimpleEditorState(rx.State):
    html_content: str = "<p>Edit me!</p>"

    def update_content(self, html: str) -> None:
        self.html_content = html
        print(f"Content updated: {len(html)} characters")


def simple_editor_demo() -> rx.Component:
    return rx.vstack(
        rx.heading("Simple Editor"),
        mn.simple_rich_text_editor(
            content=SimpleEditorState.html_content,
            on_update=SimpleEditorState.update_content,
            placeholder="Type something...",
        ),
        rx.text(f"Character count: {SimpleEditorState.html_content.length()}"),
        spacing="4",
    )
```

### Read-Only Display

```python
mn.memoized_rich_text_editor(
    mn.rich_text_editor_content(),
    content="<h2>Read-Only Content</h2><p>Cannot be edited.</p>",
    editable=False,
)
```

---

## Controlled Mode

The editor content is always controlled by your Reflex state. Use the `on_update` callback to sync changes:

```python
class ControlledEditorState(rx.State):
    content: str = "<p>Initial content</p>"
    last_saved: str = ""

    def handle_change(self, html: str) -> None:
        """Called on every content change."""
        self.content = html

    def save_content(self) -> None:
        """Save current content."""
        self.last_saved = self.content
        # Save to database, API, etc.

    def reset_content(self) -> None:
        """Reset to last saved."""
        self.content = self.last_saved


def controlled_demo() -> rx.Component:
    return rx.vstack(
        mn.simple_rich_text_editor(
            content=ControlledEditorState.content,
            on_update=ControlledEditorState.handle_change,
        ),
        rx.hstack(
            rx.button("Save", on_click=ControlledEditorState.save_content),
            rx.button("Reset", on_click=ControlledEditorState.reset_content),
        ),
    )
```

---

## Custom Toolbar

Build your own toolbar configuration:

```python
mn.memoized_rich_text_editor(
    # Toolbar
    mn.rich_text_editor_toolbar(
        # Text formatting group
        mn.rich_text_editor_controls_group(
            mn.rich_text_editor_bold(),
            mn.rich_text_editor_italic(),
            mn.rich_text_editor_underline(),
            mn.rich_text_editor_strikethrough(),
        ),

        # Heading group
        mn.rich_text_editor_controls_group(
            mn.rich_text_editor_h2(),
            mn.rich_text_editor_h3(),
        ),

        # List group
        mn.rich_text_editor_controls_group(
            mn.rich_text_editor_bullet_list(),
            mn.rich_text_editor_ordered_list(),
        ),

        # History group
        mn.rich_text_editor_controls_group(
            mn.rich_text_editor_undo(),
            mn.rich_text_editor_redo(),
        ),

        sticky=True,
        sticky_offset="60px",  # Account for fixed header
    ),

    # Content area
    mn.rich_text_editor_content(),

    content=State.content,
    on_update=State.handle_update,
)
```

---

## Available Controls

### Text Formatting

- `rich_text_editor_bold()` - **Bold** text
- `rich_text_editor_italic()` - *Italic* text
- `rich_text_editor_underline()` - Underlined text
- `rich_text_editor_strikethrough()` - ~~Strikethrough~~ text
- `rich_text_editor_code()` - `Inline code`
- `rich_text_editor_highlight()` - Highlighted text
- `rich_text_editor_clear_formatting()` - Remove all formatting

### Headings

- `rich_text_editor_h1()` through `rich_text_editor_h6()` - Heading levels 1-6

### Lists

- `rich_text_editor_bullet_list()` - Unordered list
- `rich_text_editor_ordered_list()` - Numbered list

### Blocks

- `rich_text_editor_blockquote()` - Blockquote
- `rich_text_editor_code_block()` - Code block
- `rich_text_editor_hr()` - Horizontal rule

### Links

- `rich_text_editor_link()` - Insert/edit link
- `rich_text_editor_unlink()` - Remove link

### Text Alignment

- `rich_text_editor_align_left()` - Align left
- `rich_text_editor_align_center()` - Center align
- `rich_text_editor_align_right()` - Align right
- `rich_text_editor_align_justify()` - Justify

### Subscript/Superscript

- `rich_text_editor_subscript()` - Subscript (H₂O)
- `rich_text_editor_superscript()` - Superscript (E=mc²)

### Colors

- `rich_text_editor_color_picker(colors=[...])` - Color picker dropdown
- `rich_text_editor_color(color="#FF0000")` - Apply specific color
- `rich_text_editor_unset_color()` - Remove color

### History

- `rich_text_editor_undo()` - Undo last action
- `rich_text_editor_redo()` - Redo last undone action

### Task Lists

- `rich_text_editor_task_list()` - Insert task list
- `rich_text_editor_task_list_lift()` - Decrease indent
- `rich_text_editor_task_list_sink()` - Increase indent

### Source Code

- `rich_text_editor_source_code()` - Toggle HTML source view

---

## Extensions

The editor comes with common extensions pre-loaded. Here's what's included:

### Included by Default

- **StarterKit** - Essential extensions (Bold, Italic, Heading, Paragraph, etc.)
- **Link** - URL insertion and editing
- **Highlight** - Text highlighting
- **TextAlign** - Text alignment
- **Subscript** - Subscript text
- **Superscript** - Superscript text
- **Color** - Text coloring
- **TextStyle** - Text styling (for color support)
- **Placeholder** - Empty editor placeholder

### Extension-Specific Controls

Some controls require specific extensions to be loaded:

| Control | Required Extension |
|---------|-------------------|
| `rich_text_editor_highlight()` | `@tiptap/extension-highlight` (✅ included) |
| `rich_text_editor_align_*()` | `@tiptap/extension-text-align` (✅ included) |
| `rich_text_editor_color*()` | `@tiptap/extension-color` + `text-style` (✅ included) |
| `rich_text_editor_subscript()` | `@tiptap/extension-subscript` (✅ included) |
| `rich_text_editor_superscript()` | `@tiptap/extension-superscript` (✅ included) |

---

## Styling and Theming

### Visual Variants

#### Default Variant

Standard look with borders and clear separation:

```python
mn.memoized_rich_text_editor(
    ...,
    variant="default",  # This is the default
)
```

#### Subtle Variant

Borderless design with larger controls:

```python
mn.memoized_rich_text_editor(
    ...,
    variant="subtle",
)
```

### Typography Styles

Control whether to apply Mantine's typography styles to content:

```python
mn.memoized_rich_text_editor(
    ...,
    with_typography_styles=True,  # Default: applies typography
)
```

Set to `False` to use custom CSS styling for content.

### Sticky Toolbar

Make the toolbar stick to the top when scrolling:

```python
mn.rich_text_editor_toolbar(
    ...,
    sticky=True,
    sticky_offset="0px",  # Adjust for fixed headers
)
```

---

## Advanced Features

### Color Picker with Custom Colors

```python
mn.memoized_rich_text_editor(
    mn.rich_text_editor_toolbar(
        # Color picker with custom swatches
        mn.rich_text_editor_color_picker(
            colors=[
                "#000000", "#FFFFFF",
                "#FF0000", "#00FF00", "#0000FF",
                "#FFA500", "#800080", "#FFC0CB",
            ]
        ),

        # Quick color buttons
        mn.rich_text_editor_controls_group(
            mn.rich_text_editor_color(color="#FF0000"),  # Red
            mn.rich_text_editor_color(color="#00FF00"),  # Green
            mn.rich_text_editor_color(color="#0000FF"),  # Blue
        ),

        # Remove color
        mn.rich_text_editor_unset_color(),
    ),
    mn.rich_text_editor_content(),
    content=State.content,
    on_update=State.handle_update,
)
```

### Content Validation

```python
class ValidatedEditorState(rx.State):
    content: str = ""
    is_valid: bool = True
    error_message: str = ""

    def validate_and_update(self, html: str) -> None:
        # Strip HTML tags for length check
        text_only = html.replace(r'<[^>]+>', '')

        if len(text_only) < 10:
            self.is_valid = False
            self.error_message = "Content must be at least 10 characters"
        elif len(text_only) > 1000:
            self.is_valid = False
            self.error_message = "Content must be less than 1000 characters"
        else:
            self.is_valid = True
            self.error_message = ""
            self.content = html


def validated_editor() -> rx.Component:
    return rx.vstack(
        mn.simple_rich_text_editor(
            content=ValidatedEditorState.content,
            on_update=ValidatedEditorState.validate_and_update,
        ),
        rx.cond(
            ~ValidatedEditorState.is_valid,
            rx.text(
                ValidatedEditorState.error_message,
                color="red",
            ),
        ),
    )
```

### Export Content

The editor stores content as HTML. You can convert it to other formats:

```python
class ExportState(rx.State):
    html_content: str = "<p>Content</p>"

    def export_as_plain_text(self) -> str:
        # Simple HTML tag stripping (use a library for production)
        import re
        return re.sub(r'<[^>]+>', '', self.html_content)

    def export_as_markdown(self) -> str:
        # Convert HTML to Markdown (use a library like markdownify)
        # This is a simplified example
        content = self.html_content
        content = content.replace('<strong>', '**').replace('</strong>', '**')
        content = content.replace('<em>', '*').replace('</em>', '*')
        # ... more conversions
        return content
```

---

## Troubleshooting

### Editor Not Rendering

**Problem:** Editor doesn't appear or shows blank.

**Solution:**

- Ensure `mn.rich_text_editor_content()` is included in the component tree
- Check browser console for JavaScript errors
- Verify all NPM dependencies are installed

### Content Not Updating

**Problem:** Changes in the editor don't update state.

**Solution:**

- Make sure `on_update` callback is provided
- Verify the callback function is properly updating state
- Check that the state variable is reactive

### Toolbar Buttons Not Working

**Problem:** Clicking toolbar buttons has no effect.

**Solution:**

- Ensure required extensions are loaded (check [Extensions](#extensions) section)
- For color controls, verify `TextStyle` and `Color` extensions are present
- Check browser console for extension-related errors

### Sticky Toolbar Issues

**Problem:** Sticky toolbar overlaps with fixed headers.

**Solution:**

- Adjust `sticky_offset` to match your header height:

  ```python
  mn.rich_text_editor_toolbar(
      ...,
      sticky=True,
      sticky_offset="60px",  # Height of your fixed header
  )
  ```

### Custom CSS Not Applied

**Problem:** Custom styles not affecting editor content.

**Solution:**

- Set `with_typography_styles=False` to disable default styles
- Add custom CSS targeting `.mantine-RichTextEditor-content` class

---

## Best Practices

### 1. State Management

**DO:**

```python
class EditorState(rx.State):
    content: str = "<p>Initial</p>"

    def update(self, html: str) -> None:
        self.content = html
```

**DON'T:**

```python
# Don't store editor state in component props
# Don't use multiple state variables for same content
```

### 2. Performance

**DO:**

- Use `simple_rich_text_editor` for standard use cases
- Debounce auto-save operations
- Limit real-time collaboration features

**DON'T:**

- Don't create new editor instances in loops
- Don't perform heavy operations in `on_update` callback

### 3. Content Handling

**DO:**

- Sanitize HTML before saving to database
- Validate content length and structure
- Handle empty content gracefully

**DON'T:**

- Don't trust user-submitted HTML without sanitization
- Don't store excessively large documents client-side

### 4. Toolbar Design

**DO:**

- Group related controls together
- Provide essential formatting options
- Use sticky toolbar for long documents

**DON'T:**

- Don't overcrowd the toolbar
- Don't include rarely-used controls
- Don't forget undo/redo controls

### 5. Accessibility

**DO:**

- Provide clear labels for custom controls
- Support keyboard shortcuts
- Test with screen readers

**DON'T:**

- Don't remove focus indicators
- Don't disable keyboard navigation

---

## Keyboard Shortcuts

The editor supports standard keyboard shortcuts:

| Shortcut | Action |
|----------|--------|
| **Ctrl/Cmd + B** | Bold |
| **Ctrl/Cmd + I** | Italic |
| **Ctrl/Cmd + U** | Underline |
| **Ctrl/Cmd + Shift + S** | Strikethrough |
| **Ctrl/Cmd + K** | Insert link |
| **Ctrl/Cmd + Z** | Undo |
| **Ctrl/Cmd + Shift + Z** | Redo |
| **Ctrl/Cmd + Shift + C** | Code |
| **Ctrl/Cmd + Alt + 1-6** | Heading levels |

---

## Additional Resources

- **Mantine Tiptap Docs:** <https://mantine.dev/x/tiptap/>
- **Tiptap Documentation:** <https://tiptap.dev/>
- **Reflex Documentation:** <https://reflex.dev/docs/>
- **Example Page:** `/tiptap` route in the demo app

---

## Summary

The Mantine RichTextEditor component provides a production-ready WYSIWYG editor for Reflex applications with:

✅ Two easy-to-use component variants
✅ Full toolbar customization
✅ State synchronization with Reflex
✅ Comprehensive formatting controls
✅ Built-in extensions (highlighting, colors, alignment, etc.)
✅ Keyboard shortcuts support
✅ Read-only mode
✅ Sticky toolbar option

For most use cases, start with `simple_rich_text_editor` and customize as needed!
