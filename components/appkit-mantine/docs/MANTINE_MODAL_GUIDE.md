# Mantine Modal Component Guide

Comprehensive guide for the Mantine Modal component in Reflex.

## Overview

The Modal component provides an accessible overlay dialog with built-in focus management, scroll locking, and keyboard navigation. It follows WAI-ARIA recommendations for dialog accessibility.

**Documentation:** <https://mantine.dev/core/modal/>

## Installation

The Modal component is available through the `appkit_mantine` package:

```python
import appkit_mantine as mn
```

## Basic Usage

### Simple Modal

```python
import reflex as rx
import appkit_mantine as mn

class State(rx.State):
    opened: bool = False

    def open_modal(self):
        self.opened = True

    def close_modal(self):
        self.opened = False

def page():
    return rx.vstack(
        mn.modal(
            rx.text("Modal content goes here"),
            title="My Modal",
            opened=State.opened,
            on_close=State.close_modal,
        ),
        mn.button(
            "Open Modal",
            on_click=State.open_modal,
        ),
    )
```

## Component API

### Modal Props

#### Required Props

- `opened` (bool): Controls modal visibility
- `on_close` (EventHandler): Called when modal should close

#### Content Props

- `title` (str): Modal title (h2 element)
- `children` (Any): Modal body content

#### Layout Props

- `centered` (bool): Center modal vertically (default: False)
- `full_screen` (bool): Fullscreen modal (default: False)
- `size` (str | int): Modal width - "xs", "sm", "md", "lg", "xl", "auto", or CSS value (default: "md")
- `padding` (str | int): Content padding (default: "md")
- `x_offset` (str | int): Horizontal offset (default: "5vw")
- `y_offset` (str | int): Vertical offset (default: "5dvh")

#### Visual Props

- `radius` (str | int): Border radius
- `shadow` (str): Box shadow (default: "xl")
- `with_overlay` (bool): Show overlay backdrop (default: True)
- `with_close_button` (bool): Show close button (default: True)

#### Overlay Customization

- `overlay_props` (dict): Props for Overlay component
  - `backgroundOpacity` (float): Overlay opacity
  - `blur` (int | float): Overlay blur amount
  - `color` (str): Overlay color

#### Transition Props

- `transition_props` (dict): Animation configuration
  - `transition` (str): Transition type ("fade", "scale", "slide-up", etc.)
  - `duration` (int): Transition duration in ms
  - `timingFunction` (str): CSS timing function

#### Behavior Props

- `close_on_click_outside` (bool): Close on overlay click (default: True)
- `close_on_escape` (bool): Close on Escape key (default: True)
- `trap_focus` (bool): Trap focus inside modal (default: True)
- `return_focus` (bool): Return focus on close (default: True)
- `lock_scroll` (bool): Lock body scroll when open (default: True)
- `keep_mounted` (bool): Keep in DOM when closed (default: False)

#### Advanced Props

- `scroll_area_component` (Any): Custom scroll component
- `remove_scroll_props` (dict): react-remove-scroll configuration
- `close_button_props` (dict): Close button customization
- `portal_props` (dict): Portal component props
- `within_portal` (bool): Render in portal (default: True)
- `z_index` (int | str): CSS z-index (default: 200)
- `id` (str): Element ID
- `stack_id` (str): ID for Modal.Stack

#### Lifecycle Events

- `on_enter_transition_end` (EventHandler): Called when enter transition ends
- `on_exit_transition_end` (EventHandler): Called when exit transition ends

## Common Patterns

### Centered Modal

```python
mn.modal(
    rx.text("Centered content"),
    title="Centered Modal",
    opened=State.opened,
    on_close=State.close_modal,
    centered=True,
)
```

### Fullscreen Modal

```python
mn.modal(
    rx.text("Fullscreen content"),
    title="Fullscreen",
    opened=State.opened,
    on_close=State.close_modal,
    full_screen=True,
    radius=0,
    transition_props={"transition": "fade", "duration": 200},
)
```

### Custom Size

```python
# Predefined sizes
mn.modal(
    ...,
    size="xl",  # xs, sm, md, lg, xl
)

# Custom sizes
mn.modal(
    ...,
    size="70%",  # Percentage
)

mn.modal(
    ...,
    size="50rem",  # CSS value
)

# Auto size (fits content)
mn.modal(
    ...,
    size="auto",
)
```

### Modal Without Header

```python
mn.modal(
    rx.text("Modal without header. Press Escape to close."),
    opened=State.opened,
    on_close=State.close_modal,
    with_close_button=False,  # Removes title and close button
)
```

### Custom Overlay

```python
mn.modal(
    rx.text("Content"),
    title="Custom Overlay",
    opened=State.opened,
    on_close=State.close_modal,
    overlay_props={
        "backgroundOpacity": 0.55,
        "blur": 3,
    },
)
```

### Custom Transitions

```python
# Fade transition
mn.modal(
    ...,
    transition_props={
        "transition": "fade",
        "duration": 600,
        "timingFunction": "linear",
    },
)

# Scale transition
mn.modal(
    ...,
    transition_props={
        "transition": "scale",
        "duration": 300,
    },
)
```

### Lifecycle Callbacks

```python
class State(rx.State):
    modal_data: dict = {}

    def close_modal(self):
        self.opened = False

    def clear_data(self):
        """Called after exit transition completes."""
        self.modal_data = {}

mn.modal(
    rx.text(State.modal_data.get("message", "")),
    title=State.modal_data.get("title", ""),
    opened=State.opened,
    on_close=State.close_modal,
    on_exit_transition_end=State.clear_data,
)
```

### Control Modal Behavior

```python
mn.modal(
    rx.text("Content"),
    title="Custom Behavior",
    opened=State.opened,
    on_close=State.close_modal,
    # Disable various behaviors
    close_on_click_outside=False,  # Don't close on overlay click
    close_on_escape=False,          # Don't close on Escape
    trap_focus=False,               # Don't trap focus
    return_focus=False,             # Don't return focus on close
)
```

## Compound Components

For full control over modal rendering, use compound components:

```python
mn.modal.root(
    mn.modal.overlay(),
    mn.modal.content(
        mn.modal.header(
            mn.modal.title("Custom Modal"),
            mn.modal.close_button(
                aria_label="Close modal",
            ),
        ),
        mn.modal.body(
            rx.vstack(
                rx.text("Custom modal body"),
                mn.button.button("Action", on_click=State.handle_action),
                spacing="3",
            ),
        ),
    ),
    opened=State.opened,
    on_close=State.close_modal,
)
```

### Compound Components API

#### Modal.Root

Context provider for compound components. Accepts same props as Modal except `title`, `children`, `with_close_button`.

#### Modal.Overlay

Renders the overlay backdrop.

Props:

- `background_opacity` (float): Opacity
- `blur` (int | float): Blur amount
- `color` (str): Background color
- `gradient` (str): Background gradient
- `z_index` (int): z-index value

#### Modal.Content

Main modal container. Should contain Header and Body.

Props:

- `size` (str | int): Width
- `padding` (str | int): Padding
- `radius` (str | int): Border radius
- `shadow` (str): Box shadow

#### Modal.Header

Sticky header container (usually contains Title and CloseButton).

#### Modal.Title

Title element (h2) with proper ARIA attributes.

#### Modal.CloseButton

Close button for the modal.

Props:

- `aria_label` (str): Accessibility label (default: "Close modal")
- `icon` (Any): Custom icon component
- `on_click` (EventHandler): Click handler

#### Modal.Body

Content container with proper ARIA attributes.

## Modal.Stack - Multiple Modals

Modal.Stack manages multiple modals with automatic z-index and focus management:

```python
class State(rx.State):
    first_opened: bool = False
    second_opened: bool = False
    third_opened: bool = False

    def close_all(self):
        self.first_opened = False
        self.second_opened = False
        self.third_opened = False

mn.modal.stack(
    mn.modal(
        rx.vstack(
            rx.text("First modal"),
            mn.button.button(
                "Open Second",
                on_click=State.set_second_opened(True),
            ),
            spacing="3",
        ),
        title="First",
        opened=State.first_opened,
        on_close=State.set_first_opened(False),
        stack_id="first",
    ),
    mn.modal(
        rx.vstack(
            rx.text("Second modal"),
            mn.button.button(
                "Open Third",
                on_click=State.set_third_opened(True),
            ),
            spacing="3",
        ),
        title="Second",
        opened=State.second_opened,
        on_close=State.set_second_opened(False),
        stack_id="second",
    ),
    mn.modal(
        rx.vstack(
            rx.text("Third modal"),
            mn.button.button(
                "Close All",
                on_click=State.close_all,
            ),
            spacing="3",
        ),
        title="Third",
        opened=State.third_opened,
        on_close=State.set_third_opened(False),
        stack_id="third",
    ),
)
```

**Note:** Modal.Stack only works with Modal component, not Modal.Root compound components.

## Accessibility

Modal follows WAI-ARIA dialog recommendations:

### Automatic Features

- Focus is trapped inside the modal
- Focus returns to trigger element on close
- Escape key closes the modal
- Proper ARIA attributes (role="dialog", aria-modal="true")
- Title linked via aria-labelledby
- Body linked via aria-describedby

### Custom Close Button Label

```python
mn.modal(
    ...,
    close_button_props={
        "aria-label": "Close authentication modal",
    },
)
```

### Initial Focus

Add `data-autofocus` to the element that should receive initial focus:

```python
mn.modal(
    rx.vstack(
        mn.form.input(label="Username"),
        mn.form.input(
            label="Password (focused)",
            data_autofocus=True,  # This receives initial focus
        ),
        spacing="3",
    ),
    title="Login",
    opened=State.opened,
    on_close=State.close_modal,
)
```

### No Initial Focus

Use FocusTrap.InitialFocus for visually hidden initial focus element:

```python
mn.modal(
    rx.vstack(
        rx.FocusTrap.InitialFocus(),  # Hidden element receives focus
        mn.form.input(label="Username"),
        mn.form.input(label="Password"),
        spacing="3",
    ),
    title="Login",
    opened=State.opened,
    on_close=State.close_modal,
)
```

## Best Practices

### When to Use Modal

✅ **Use Modal for:**

- Confirmation dialogs
- Forms requiring full user attention
- Critical information display
- Multi-step workflows
- Authentication flows

❌ **Don't use Modal for:**

- Side panels (use Drawer)
- Simple notifications (use Toast/Notification)
- Inline editing (use inline forms)
- Non-blocking actions

### Performance

```python
# ✅ Good: Keep mounted for frequently toggled modals
mn.modal(
    ...,
    keep_mounted=True,  # Stays in DOM, display: none when closed
)

# ✅ Good: Unmount for rarely used modals (default)
mn.modal(
    ...,
    keep_mounted=False,  # Unmounted from DOM when closed
)
```

### State Management

```python
class State(rx.State):
    # ✅ Good: Separate state for each modal
    login_opened: bool = False
    signup_opened: bool = False

    # ✅ Good: Clear form data after transition
    form_data: dict = {}

    def close_login(self):
        self.login_opened = False

    def clear_form(self):
        """Called via on_exit_transition_end."""
        self.form_data = {}
```

### Size Guidelines

```python
# Small content (confirmation)
size="sm"  # ~500px

# Medium content (forms)
size="md"  # ~640px (default)

# Large content (detailed info)
size="lg"  # ~800px

# Extra large (complex forms)
size="xl"  # ~1140px

# Responsive
size="90%"  # Percentage of viewport
```

## Common Use Cases

### Confirmation Dialog

```python
def delete_confirmation() -> rx.Component:
    return mn.modal(
        rx.vstack(
            rx.text("Are you sure you want to delete this item?"),
            rx.text("This action cannot be undone.", color="gray"),
            rx.hstack(
                mn.button.button(
                    "Cancel",
                    on_click=State.close_modal,
                    variant="outline",
                ),
                mn.button.button(
                    "Delete",
                    on_click=State.confirm_delete,
                    color="red",
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
            spacing="4",
        ),
        title="Confirm Deletion",
        opened=State.delete_modal_opened,
        on_close=State.close_modal,
        centered=True,
    )
```

### Form Modal

```python
def user_form_modal() -> rx.Component:
    return mn.modal(
        rx.vstack(
            mn.form.input(
                label="Username",
                value=State.username,
                on_change=State.set_username,
                required=True,
            ),
            mn.form.input(
                label="Email",
                value=State.email,
                on_change=State.set_email,
                type="email",
                required=True,
            ),
            mn.form.textarea(
                label="Bio",
                value=State.bio,
                on_change=State.set_bio,
            ),
            rx.hstack(
                mn.button.button(
                    "Cancel",
                    on_click=State.close_modal,
                    variant="outline",
                ),
                mn.button.button(
                    "Save",
                    on_click=State.save_user,
                ),
                spacing="3",
                justify="end",
                width="100%",
            ),
            spacing="4",
        ),
        title="Edit Profile",
        opened=State.form_modal_opened,
        on_close=State.close_modal,
        size="lg",
    )
```

## Troubleshooting

### Modal Not Closing

- Ensure `on_close` handler updates the `opened` state
- Check if `close_on_click_outside` or `close_on_escape` are disabled

### Focus Issues

- Verify `trap_focus` is enabled (default)
- Add `data-autofocus` to desired element
- Check for competing focus management

### Scroll Lock Not Working

- Ensure `lock_scroll` is enabled (default)
- Check for CSS overflow conflicts
- Verify `remove_scroll_props` configuration

### Z-Index Conflicts

- Adjust `z_index` prop (default: 200)
- Use Modal.Stack for multiple modals
- Check for competing fixed/sticky elements

## Examples

See [modal_examples.py](../../app/pages/examples/modal_examples.py) for comprehensive examples including:

- Basic modal
- Centered modal
- Fullscreen modal
- Custom sizes
- Custom overlay
- Compound components
- Modal.Stack with multiple modals

## Related Components

- **Drawer**: Side panel overlay
- **Popover**: Floating content
- **Dialog**: Simple confirmation dialogs (Radix UI)
- **Toast/Notification**: Non-blocking notifications

## References

- [Mantine Modal Documentation](https://mantine.dev/core/modal/)
- [WAI-ARIA Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
- [react-remove-scroll](https://github.com/theKashey/react-remove-scroll)
