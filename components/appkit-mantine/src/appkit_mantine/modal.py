"""Mantine Modal component wrapper for Reflex.

An accessible overlay dialog component with full ARIA support. Modal follows
WAI-ARIA recommendations and includes focus management, scroll locking, and
keyboard navigation out of the box.

Key Features:
    - Automatic focus trapping and return focus
    - Scroll locking with react-remove-scroll
    - Customizable overlay and transitions
    - Compound components for full control
    - Modal.Stack for multiple modals
    - Full accessibility support

Documentation: https://mantine.dev/core/modal/

Example:
    ```python
    import reflex as rx
    import appkit_mantine as mn


    class State(rx.State):
        opened: bool = False

        def open_modal(self):
            self.opened = True

        def close_modal(self):
            self.opened = False


    def my_page():
        return mn.stack(
            mn.modal(
                rx.text("Modal content goes here"),
                title="My Modal",
                opened=State.opened,
                on_close=State.close_modal,
                centered=True,
            ),
            mn.button(
                "Open Modal",
                on_click=State.open_modal,
            ),
        )
    ```
"""

from __future__ import annotations

from typing import Any

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineComponentBase, MantineOverlayComponentBase

# ============================================================================
# Modal Component
# ============================================================================


class Modal(MantineOverlayComponentBase):
    """Mantine Modal component - accessible overlay dialog.

    Based on: https://mantine.dev/core/modal/

    Modal provides a dialog overlay with built-in accessibility features,
    focus management, and scroll locking. Use it for important user interactions
    that require full attention.

    Common use cases:
        - Confirmation dialogs
        - Forms that require user focus
        - Displaying detailed information
        - Multi-step workflows

    For side panels, consider using Drawer instead.
    For simple notifications, use Notification or Toast.
    """

    tag = "Modal"

    # Layout
    centered: Var[bool] = None
    """Center modal vertically."""

    full_screen: Var[bool] = None
    """Fullscreen modal."""

    x_offset: Var[str | int] = None
    """Horizontal offset."""

    y_offset: Var[str | int] = None
    """Vertical offset."""

    # Stack
    stack_id: Var[str]
    """ID for Modal.Stack."""


# ============================================================================
# Modal Compound Components
# ============================================================================


class ModalRoot(MantineOverlayComponentBase):
    """Modal.Root - Context provider for compound Modal components.

    Use with other Modal.* components for full control over modal rendering.
    This is the container component that provides context to all child components.

    Example:
        ```python
        mn.modal.root(
            mn.modal.overlay(),
            mn.modal.content(
                mn.modal.header(
                    mn.modal.title("My Title"),
                    mn.modal.close_button(),
                ),
                mn.modal.body("Content here"),
            ),
            opened=State.opened,
            on_close=State.close_modal,
        )
        ```
    """

    tag = "Modal.Root"

    # Behavior
    centered: Var[bool] = None
    full_screen: Var[bool] = None
    x_offset: Var[str | int] = None
    y_offset: Var[str | int] = None

    stack_id: Var[str]


class ModalOverlay(MantineComponentBase):
    """Modal.Overlay - Overlay backdrop for modal.

    Renders a semi-transparent overlay behind the modal content.
    Customize appearance with props like backgroundOpacity and blur.

    Example:
        ```python
        mn.modal.overlay(
            background_opacity=0.55,
            blur=3,
        )
        ```
    """

    tag = "Modal.Overlay"

    # Overlay styling
    background_opacity: Var[float]
    blur: Var[int | float]
    color: Var[str]
    gradient: Var[str]
    z_index: Var[int]


class ModalContent(MantineComponentBase):
    """Modal.Content - Main modal container.

    Contains all modal content including header and body.
    Should be used inside Modal.Root.

    The content element has aria-modal="true" and proper ARIA attributes
    for accessibility.
    """

    tag = "Modal.Content"

    # Layout
    size: Var[str | int] = "md"
    padding: Var[str | int] = "md"
    radius: Var[str | int]
    shadow: Var[str] = "xl"


class ModalHeader(MantineComponentBase):
    """Modal.Header - Sticky header container.

    Usually contains Modal.Title and Modal.CloseButton.
    The header stays visible when content scrolls.

    Example:
        ```python
        mn.modal.header(
            mn.modal.title("My Title"),
            mn.modal.close_button(),
        )
        ```
    """

    tag = "Modal.Header"


class ModalTitle(MantineComponentBase):
    """Modal.Title - Modal title element (h2).

    The title is automatically linked via aria-labelledby to the content
    element for accessibility.

    Example:
        ```python
        mn.modal.title("Confirm Action")
        ```
    """

    tag = "Modal.Title"


class ModalCloseButton(MantineComponentBase):
    """Modal.CloseButton - Close button for modal.

    Automatically positioned in the header. Customize with standard
    button props like icon, aria-label, etc.

    Example:
        ```python
        mn.modal.close_button(
            aria_label="Close modal",
        )
        ```
    """

    tag = "Modal.CloseButton"

    # Accessibility
    aria_label: Var[str] = "Close modal"

    # Custom icon
    icon: Var[Any]

    # Event handler
    on_click: EventHandler[rx.event.no_args_event_spec]


class ModalBody(MantineComponentBase):
    """Modal.Body - Modal content container.

    Contains the main modal content. The body is automatically linked
    via aria-describedby to the content element for accessibility.

    Example:
        ```python
        mn.modal.body(
            rx.text("Are you sure you want to delete this item?"),
            rx.button("Confirm", on_click=State.confirm),
        )
        ```
    """

    tag = "Modal.Body"


# ============================================================================
# Modal.Stack for Multiple Modals
# ============================================================================


class ModalStack(MantineComponentBase):
    """Modal.Stack - Container for managing multiple modals.

    Modal.Stack manages z-index, focus trapping, and escape key handling
    for multiple modals. Only the top modal receives focus and can be closed.

    Use with useModalsStack hook in JavaScript or manage state manually in Reflex.

    Key features:
        - Automatic z-index management
        - Focus trap only on top modal
        - Escape closes only top modal
        - Single shared overlay
        - Hidden modals stay in DOM (opacity: 0)

    Example:
        ```python
        class StackState(rx.State):
            first_opened: bool = False
            second_opened: bool = False


        mn.modal.stack(
            mn.modal.modal(
                rx.text("First modal"),
                opened=StackState.first_opened,
                on_close=StackState.set_first_opened(False),
                stack_id="first",
            ),
            mn.modal.modal(
                rx.text("Second modal"),
                opened=StackState.second_opened,
                on_close=StackState.set_second_opened(False),
                stack_id="second",
            ),
        )
        ```

    Note: Modal.Stack only works with Modal component, not with Modal.Root
    compound components.
    """

    tag = "Modal.Stack"


# ============================================================================
# Convenience Functions & Namespace
# ============================================================================


class ModalNamespace(rx.ComponentNamespace):
    """Namespace for Modal components.

    Provides convenient access to all Modal components and sub-components.

    Usage:
        ```python
        import appkit_mantine as mn

        # Simple modal
        mn.modal(...)

        # Compound components
        mn.modal.root(
            mn.modal.overlay(),
            mn.modal.content(
                mn.modal.header(...),
                mn.modal.body(...),
            ),
        )

        # Multiple modals
        mn.modal.stack(...)
        ```
    """

    # Main component
    __call__ = staticmethod(Modal.create)

    # Compound components
    root = staticmethod(ModalRoot.create)
    overlay = staticmethod(ModalOverlay.create)
    content = staticmethod(ModalContent.create)
    header = staticmethod(ModalHeader.create)
    title = staticmethod(ModalTitle.create)
    close_button = staticmethod(ModalCloseButton.create)
    body = staticmethod(ModalBody.create)

    # Stack
    stack = staticmethod(ModalStack.create)


modal = ModalNamespace()
