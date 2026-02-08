"""Mantine navigation components."""

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import (
    MANTINE_VERSION,
    MantineComponentBase,
    MantineLayoutComponentBase,
)


class Breadcrumbs(MantineLayoutComponentBase):
    """Mantine Breadcrumbs component."""

    tag = "Breadcrumbs"

    separator: Var[str | rx.Component]
    separator_margin: Var[str | int]


class Pagination(MantineLayoutComponentBase):
    """Mantine Pagination component."""

    tag = "Pagination"

    total: Var[int]
    value: Var[int]
    default_value: Var[int]
    siblings: Var[int]
    boundaries: Var[int]
    color: Var[str]
    radius: Var[str | int]
    size: Var[str | int]
    with_edges: Var[bool]
    with_controls: Var[bool]

    on_change: EventHandler[lambda value: [value]]


class Stepper(MantineLayoutComponentBase):
    """Mantine Stepper component."""

    tag = "Stepper"

    active: Var[int]
    completed_icon: Var[Any]
    icon: Var[Any]
    orientation: Var[Literal["horizontal", "vertical"]]
    icon_size: Var[int]
    size: Var[str | int]
    radius: Var[str | int]
    color: Var[str]
    allow_next_steps_select: Var[bool]

    on_step_click: EventHandler[lambda step: [step]]


class StepperStep(MantineLayoutComponentBase):
    """Mantine Stepper.Step component."""

    tag = "Stepper.Step"

    label: Var[str]
    description: Var[str]
    icon: Var[Any]
    completed_icon: Var[Any]
    loading: Var[bool]
    allow_step_select: Var[bool]


class StepperCompleted(MantineLayoutComponentBase):
    """Mantine Stepper.Completed component."""

    tag = "Stepper.Completed"


class Tabs(MantineLayoutComponentBase):
    """Mantine Tabs component."""

    tag = "Tabs"

    value: Var[str]
    default_value: Var[str]
    orientation: Var[Literal["horizontal", "vertical"]]
    color: Var[str]
    radius: Var[str | int]
    inverted: Var[bool]
    variant: Var[str]  # default, outline, pills
    keep_mounted: Var[bool]

    on_change: EventHandler[lambda value: [value]]


class TabsList(MantineLayoutComponentBase):
    """Mantine Tabs.List component."""

    tag = "Tabs.List"

    grow: Var[bool]
    justify: Var[str]


class TabsTab(MantineLayoutComponentBase):
    """Mantine Tabs.Tab component."""

    tag = "Tabs.Tab"

    value: Var[str]
    left_section: Var[Any]
    right_section: Var[Any]
    color: Var[str]
    disabled: Var[bool]


class TabsPanel(MantineLayoutComponentBase):
    """Mantine Tabs.Panel component."""

    tag = "Tabs.Panel"

    value: Var[str]
    keep_mounted: Var[bool]


class StepperNamespace(rx.ComponentNamespace):
    """Namespace for Stepper components."""

    step = staticmethod(StepperStep.create)
    completed = staticmethod(StepperCompleted.create)

    __call__ = staticmethod(Stepper.create)


class TabsNamespace(rx.ComponentNamespace):
    """Namespace for Tabs components."""

    list = staticmethod(TabsList.create)
    tab = staticmethod(TabsTab.create)
    panel = staticmethod(TabsPanel.create)

    __call__ = staticmethod(Tabs.create)


class NavigationProgress(MantineComponentBase):
    """Mantine NavigationProgress component - top navigation progress bar.

    Based on: https://mantine.dev/x/nprogress/

    This component renders a progress bar at the top of the page that can be
    controlled imperatively using nprogress utility functions (start, stop,
    increment, decrement, set, reset, complete).

    The component must be rendered within MantineProvider and should typically
    be placed at the root level of your application.

    Example:
        ```python
        import reflex as rx
        from mantine import navigation_progress


        def index():
            return rx.fragment(
                navigation_progress(),
                # Your app content here
            )
        ```

    Control the progress bar using custom events:
        ```python
        class State(rx.State):
            def start_loading(self):
                return rx.call_script("window.nprogress.start()")

            def complete_loading(self):
                return rx.call_script("window.nprogress.complete()")
        ```
    """

    tag = "NavigationProgress"
    library = f"@mantine/nprogress@{MANTINE_VERSION}"

    def _get_custom_code(self) -> str:
        return """import '@mantine/core/styles.css';
import '@mantine/nprogress/styles.css';
import { nprogress } from '@mantine/nprogress';

// Expose nprogress API globally for Reflex control via rx.call_script()
if (typeof window !== 'undefined') {
    window.nprogress = nprogress;
}"""

    # Color and styling
    color: Var[str] = None
    """Progress bar color (Mantine color name or CSS color)."""

    size: Var[int | str] = None
    """Progress bar height in pixels (default: 4)."""

    # Progress bar behavior
    with_transition: Var[bool] = None
    """Enable smooth transitions (default: true)."""

    step_interval: Var[int] = None
    """Auto-increment interval in milliseconds when using start()."""

    # Position
    z_index: Var[int] = None
    """CSS z-index for the progress bar (default: 9999)."""

    # Initial state
    initial_progress: Var[int] = None
    """Initial progress value (0-100)."""


class NavLink(MantineComponentBase):
    """Mantine NavLink wrapper for Reflex.

    See: https://mantine.dev/core/nav-link/

    Supports label, description, icon, right_section, children (nested links),
    opened/default_opened control, active/disabled states, styles and sx.
    """

    tag = "NavLink"

    # Prop renames from snake_case to camelCase / React names
    _rename_props = {
        "aria_label": "aria-label",
        "right_section": "rightSection",
        "default_opened": "defaultOpened",
        "initially_opened": "initiallyOpened",
        "chevron_position": "chevronPosition",
    }

    # Basic content
    label: Var[str] = None
    description: Var[str] = None
    icon: Var[Any] = None
    left_section: Var[Any] = None
    right_section: Var[Any] = None
    children: Var[Any] = None

    # Open/active state control
    opened: Var[bool] = None
    default_opened: Var[bool] = None
    initially_opened: Var[bool] = None
    active: Var[bool] = None

    # Visual props
    variant: Var[Literal["default", "filled", "subtle", "outline"]] = None
    color: Var[str] = None
    radius: Var[str] = None
    disabled: Var[bool] = None

    # Chevron position (left/right)
    chevron_position: Var[Literal["left", "right"]] = None

    # Transitions
    transition_duration: Var[int] = None

    # Event handlers
    on_click: EventHandler = None

    # Styling hooks
    styles: Var[dict] = None
    sx: Var[dict] = None


# Convenience factory to match other components' usage

breadcrumbs = Breadcrumbs.create
navigation_progress = NavigationProgress.create
nav_link = NavLink.create
pagination = Pagination.create
stepper = StepperNamespace()
tabs = TabsNamespace()
