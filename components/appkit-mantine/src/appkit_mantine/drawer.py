"""Mantine Drawer wrapper for Reflex.

Docs: https://mantine.dev/core/drawer/
"""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx

from appkit_mantine.base import MantineComponentBase, MantineOverlayComponentBase


class Drawer(MantineOverlayComponentBase):
    """Reflex wrapper for Mantine Drawer.

    Display overlay area at any side of the screen.

    Example:
        ```
        from appkit_mantine import drawer
        import reflex as rx


        class State(rx.State):
            drawer_opened: bool = False

            def open_drawer(self):
                self.drawer_opened = True

            def close_drawer(self):
                self.drawer_opened = False


        def index():
            return rx.fragment(
                drawer(
                    "Drawer content here",
                    opened=State.drawer_opened,
                    on_close=State.close_drawer,
                    title="Authentication",
                ),
                rx.button("Open Drawer", on_click=State.open_drawer),
            )
        ```
    """

    tag = "Drawer"

    # ========================================================================
    # Specific Props
    # ========================================================================

    position: rx.Var[Literal["left", "right", "top", "bottom"]]
    """Drawer position (default: 'left')."""

    offset: rx.Var[int | str]
    """Offset from viewport edge in px."""


class DrawerRoot(MantineOverlayComponentBase):
    """Drawer.Root - Context provider for compound drawer components."""

    tag = "Drawer.Root"

    position: rx.Var[Literal["left", "right", "top", "bottom"]]
    """Drawer position."""


class DrawerOverlay(MantineComponentBase):
    """Drawer.Overlay - Overlay component for compound drawer."""

    tag = "Drawer.Overlay"

    background_opacity: rx.Var[float]
    """Overlay background opacity (0-1)."""

    blur: rx.Var[int]
    """Backdrop blur amount in px."""

    color: rx.Var[str]
    """Overlay background color."""

    z_index: rx.Var[int | str]
    """CSS z-index."""

    _rename_props = {
        "background_opacity": "backgroundOpacity",
        "z_index": "zIndex",
    }


class DrawerContent(MantineComponentBase):
    """Drawer.Content - Main drawer element for compound drawer."""

    tag = "Drawer.Content"

    padding: rx.Var[Literal["xs", "sm", "md", "lg", "xl"] | int | str]  # noqa: PYI051
    """Content padding."""

    radius: rx.Var[Literal["xs", "sm", "md", "lg", "xl"] | int | str]  # noqa: PYI051
    """Border radius."""

    shadow: rx.Var[Literal["xs", "sm", "md", "lg", "xl"]]
    """Box shadow."""


class DrawerHeader(MantineComponentBase):
    """Drawer.Header - Sticky header for compound drawer."""

    tag = "Drawer.Header"


class DrawerTitle(MantineComponentBase):
    """Drawer.Title - Title element for compound drawer."""

    tag = "Drawer.Title"


class DrawerCloseButton(MantineComponentBase):
    """Drawer.CloseButton - Close button for compound drawer."""

    tag = "Drawer.CloseButton"

    icon: rx.Var[Any]
    """Custom icon element."""

    aria_label: rx.Var[str]
    """Accessibility label."""

    _rename_props = {
        "aria_label": "aria-label",
    }


class DrawerBody(MantineComponentBase):
    """Drawer.Body - Main content area for compound drawer."""

    tag = "Drawer.Body"


class DrawerStack(MantineComponentBase):
    """Drawer.Stack - Container for multiple stacked drawers.

    Manages z-index, focus trapping, and Escape key handling for multiple drawers.

    Example:
        ```
        from appkit_mantine import drawer
        import reflex as rx


        def demo():
            # Use the hook to manage multiple drawers
            # stack = use_drawers_stack(['delete-page', 'confirm-action'])

            return drawer.stack(
                drawer(
                    "Delete this page?",
                    # **stack.register('delete-page'),
                    title="Delete page",
                ),
                drawer(
                    "Confirm action",
                    # **stack.register('confirm-action'),
                    title="Confirm",
                ),
            )
        ```
    """

    tag = "Drawer.Stack"


# ============================================================================
# Drawer Namespace
# ============================================================================


class DrawerNamespace(rx.ComponentNamespace):
    """Namespace for Drawer components."""

    # Main drawer component (default when using drawer())
    __call__ = staticmethod(Drawer.create)

    # Compound components
    root = staticmethod(DrawerRoot.create)
    overlay = staticmethod(DrawerOverlay.create)
    content = staticmethod(DrawerContent.create)
    header = staticmethod(DrawerHeader.create)
    title = staticmethod(DrawerTitle.create)
    close_button = staticmethod(DrawerCloseButton.create)
    body = staticmethod(DrawerBody.create)
    stack = staticmethod(DrawerStack.create)


drawer = DrawerNamespace()
