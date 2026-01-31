"""Mantine Drawer wrapper for Reflex.

Docs: https://mantine.dev/core/drawer/
"""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx

from appkit_mantine.base import MantineComponentBase


class Drawer(MantineComponentBase):
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
    # Core Props - State and behavior
    # ========================================================================

    opened: rx.Var[bool]
    """Controls whether drawer is opened (required for controlled component)."""

    title: rx.Var[str]
    """Drawer title displayed in header."""

    with_close_button: rx.Var[bool]
    """Whether to show close button in header (default: True)."""

    with_overlay: rx.Var[bool]
    """Whether to show overlay behind drawer (default: True)."""

    # ========================================================================
    # Position and Layout Props
    # ========================================================================

    position: rx.Var[Literal["left", "right", "top", "bottom"]]
    """Drawer position (default: 'left')."""

    size: rx.Var[str | int | Literal["xs", "sm", "md", "lg", "xl", "full"]]  # noqa: PYI051
    """Drawer size (width for left/right, height for top/bottom).
    Can be predefined size or custom value (e.g., '55%', 200)."""

    offset: rx.Var[int | str]
    """Offset from viewport edge in px."""

    # ========================================================================
    # Visual Styling Props
    # ========================================================================

    radius: rx.Var[Literal["xs", "sm", "md", "lg", "xl"] | int | str]  # noqa: PYI051
    """Border radius size."""

    padding: rx.Var[Literal["xs", "sm", "md", "lg", "xl"] | int | str]  # noqa: PYI051
    """Drawer content padding."""

    shadow: rx.Var[Literal["xs", "sm", "md", "lg", "xl"]]
    """Box shadow size."""

    z_index: rx.Var[int | str]
    """CSS z-index property."""

    # ========================================================================
    # Overlay Props
    # ========================================================================

    overlay_props: rx.Var[dict[str, Any]]
    """Props passed to Overlay component (e.g., {'backgroundOpacity':0.5, 'blur':4})."""

    # ========================================================================
    # Scroll Behavior Props
    # ========================================================================

    scroll_area_component: rx.Var[Any]
    """Custom scroll area component (e.g., ScrollArea.Autosize)."""

    lock_scroll: rx.Var[bool]
    """Whether to lock scroll on mount (default: True)."""

    # ========================================================================
    # Transition Props
    # ========================================================================

    transition_props: rx.Var[dict[str, Any]]
    """Props for Transition component (e.g., {'transition': 'fade','duration': 200})."""

    # ========================================================================
    # Focus Management Props
    # ========================================================================

    trap_focus: rx.Var[bool]
    """Whether to trap focus inside drawer (default: True)."""

    return_focus: rx.Var[bool]
    """Whether to return focus to trigger element on close (default: True)."""

    # ========================================================================
    # Interaction Props
    # ========================================================================

    close_on_escape: rx.Var[bool]
    """Whether to close drawer on Escape key press (default: True)."""

    close_on_click_outside: rx.Var[bool]
    """Whether to close drawer on overlay click (default: True)."""

    with_close_on_escape: rx.Var[bool]
    """Alias for close_on_escape (deprecated, use close_on_escape)."""

    # ========================================================================
    # Close Button Props
    # ========================================================================

    close_button_props: rx.Var[dict[str, Any]]
    """Props for close button (e.g., {'icon': <Icon />, 'aria-label': 'Close'})."""

    # ========================================================================
    # Advanced Props
    # ========================================================================

    keep_mounted: rx.Var[bool]
    """Whether to keep drawer mounted in DOM when closed (default: False)."""

    remove_scroll_props: rx.Var[dict[str, Any]]
    """Props passed to react-remove-scroll (e.g., {'allowPinchZoom': True})."""

    portal_props: rx.Var[dict[str, Any]]
    """Props for Portal component."""

    # ========================================================================
    # Mantine Style Props
    # ========================================================================

    w: rx.Var[str | int]
    """Width."""

    h: rx.Var[str | int]
    """Height."""

    m: rx.Var[str | int]
    """Margin (all sides)."""

    mt: rx.Var[str | int]
    """Margin top."""

    mb: rx.Var[str | int]
    """Margin bottom."""

    ml: rx.Var[str | int]
    """Margin left."""

    mr: rx.Var[str | int]
    """Margin right."""

    mx: rx.Var[str | int]
    """Margin horizontal (left and right)."""

    my: rx.Var[str | int]
    """Margin vertical (top and bottom)."""

    # ========================================================================
    # Event Handlers
    # ========================================================================

    on_close: rx.EventHandler[rx.event.no_args_event_spec] = None
    """Called when drawer should close (overlay click, Escape key, close button)."""

    on_exit_transition_end: rx.EventHandler[rx.event.no_args_event_spec] = None
    """Called when exit transition finishes (useful for cleanup)."""

    on_enter_transition_end: rx.EventHandler[rx.event.no_args_event_spec] = None
    """Called when enter transition finishes."""

    # Prop aliasing for camelCase React props
    _rename_props = {
        "close_button_props": "closeButtonProps",
        "close_on_click_outside": "closeOnClickOutside",
        "close_on_escape": "closeOnEscape",
        "keep_mounted": "keepMounted",
        "lock_scroll": "lockScroll",
        "on_close": "onClose",
        "on_enter_transition_end": "onEnterTransitionEnd",
        "on_exit_transition_end": "onExitTransitionEnd",
        "overlay_props": "overlayProps",
        "portal_props": "portalProps",
        "remove_scroll_props": "removeScrollProps",
        "return_focus": "returnFocus",
        "scroll_area_component": "scrollAreaComponent",
        "transition_props": "transitionProps",
        "trap_focus": "trapFocus",
        "with_close_button": "withCloseButton",
        "with_close_on_escape": "withCloseOnEscape",
        "with_overlay": "withOverlay",
        "z_index": "zIndex",
    }

    def get_event_triggers(self) -> dict[str, Any]:
        """Define event triggers for the component."""
        base = super().get_event_triggers()
        base.update(
            {
                "on_close": rx.event.no_args_event_spec,
                "on_exit_transition_end": rx.event.no_args_event_spec,
                "on_enter_transition_end": rx.event.no_args_event_spec,
            }
        )
        return base


class DrawerRoot(MantineComponentBase):
    """Drawer.Root - Context provider for compound drawer components."""

    tag = "Drawer.Root"

    opened: rx.Var[bool]
    """Controls whether drawer is opened."""

    on_close: rx.EventHandler[rx.event.no_args_event_spec]
    """Called when drawer should close."""

    position: rx.Var[Literal["left", "right", "top", "bottom"]]
    """Drawer position."""

    trap_focus: rx.Var[bool]
    """Whether to trap focus inside drawer."""

    return_focus: rx.Var[bool]
    """Whether to return focus on close."""

    close_on_escape: rx.Var[bool]
    """Whether to close on Escape key."""

    close_on_click_outside: rx.Var[bool]
    """Whether to close on overlay click."""

    scroll_area_component: rx.Var[Any]
    """Custom scroll area component."""

    lock_scroll: rx.Var[bool]
    """Whether to lock scroll on mount."""

    _rename_props = {
        "trap_focus": "trapFocus",
        "return_focus": "returnFocus",
        "close_on_escape": "closeOnEscape",
        "close_on_click_outside": "closeOnClickOutside",
        "scroll_area_component": "scrollAreaComponent",
        "lock_scroll": "lockScroll",
    }


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
