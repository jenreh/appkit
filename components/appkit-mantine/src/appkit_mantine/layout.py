"""Mantine layout components."""

from typing import Any, Literal

import reflex as rx
from reflex.assets import asset
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import (
    MANTINE_LIBARY,
    MANTINE_VERSION,
    MantineComponentBase,
    MantineLayoutComponentBase,
    MantineSize,
)


class Box(MantineLayoutComponentBase):
    """Mantine Box component."""

    tag = "Box"

    component: Var[str]


class Center(MantineLayoutComponentBase):
    """Mantine Center component."""

    tag = "Center"

    inline: Var[bool]


class Container(MantineLayoutComponentBase):
    """Mantine Container component."""

    tag = "Container"

    fluid: Var[bool]
    size: Var[MantineSize | str]


class Flex(MantineLayoutComponentBase):
    """Mantine Flex component."""

    tag = "Flex"

    gap: Var[str | int | dict]
    row_gap: Var[str | int | dict]
    column_gap: Var[str | int | dict]
    align: Var[str | dict]
    justify: Var[str | dict]
    wrap: Var[str | dict]
    direction: Var[str | dict]


class Group(MantineLayoutComponentBase):
    """Mantine Group component."""

    tag = "Group"

    justify: Var[str]
    align: Var[str]
    gap: Var[str | int]
    grow: Var[bool]
    prevent_grow_overflow: Var[bool]
    wrap: Var[str]


class Stack(MantineLayoutComponentBase):
    """Mantine Stack component."""

    tag = "Stack"

    align: Var[str]
    justify: Var[str]
    gap: Var[str | int]


class SimpleGrid(MantineLayoutComponentBase):
    """Mantine SimpleGrid component."""

    tag = "SimpleGrid"

    cols: Var[int | dict]
    spacing: Var[str | int | dict]
    vertical_spacing: Var[str | int | dict]
    type: Var[Literal["container", "media"]]


class Grid(MantineLayoutComponentBase):
    """Mantine Grid component."""

    tag = "Grid"

    columns: Var[int]
    gutter: Var[str | int | dict]
    grow: Var[bool]
    justify: Var[str]
    align: Var[str]
    overflow: Var[str]
    type: Var[Literal["container", "media"]]


class GridCol(MantineLayoutComponentBase):
    """Mantine Grid.Col component."""

    tag = "Grid.Col"

    span: Var[int | str | dict]
    offset: Var[int | dict]
    order: Var[int | dict]


class Space(MantineLayoutComponentBase):
    """Mantine Space component."""

    tag = "Space"


class Divider(MantineLayoutComponentBase):
    """Mantine Divider component."""

    tag = "Divider"

    color: Var[str]
    label: Var[str]
    label_position: Var[Literal["left", "center", "right"]]
    orientation: Var[Literal["horizontal", "vertical"]]
    size: Var[str | int]
    variant: Var[Literal["solid", "dashed", "dotted"]]


class Affix(MantineLayoutComponentBase):
    """Mantine Affix component."""

    tag = "Affix"

    position: Var[dict]
    within_portal: Var[bool]
    z_index: Var[int | str]


class FocusTrap(MantineComponentBase):
    """Mantine FocusTrap component."""

    tag = "FocusTrap"

    active: Var[bool]
    ref_prop: Var[str]


class AppShellHeader(MantineLayoutComponentBase):
    """Mantine AppShell.Header."""

    tag = "AppShell.Header"

    with_border: Var[bool] = None
    z_index: Var[str | int] = None


class AppShellNavbar(MantineLayoutComponentBase):
    """Mantine AppShell.Navbar."""

    tag = "AppShell.Navbar"

    with_border: Var[bool] = None
    z_index: Var[str | int] = None


class AppShellAside(MantineLayoutComponentBase):
    """Mantine AppShell.Aside."""

    tag = "AppShell.Aside"

    with_border: Var[bool] = None
    z_index: Var[str | int] = None


class AppShellFooter(MantineLayoutComponentBase):
    """Mantine AppShell.Footer."""

    tag = "AppShell.Footer"

    with_border: Var[bool] = None
    z_index: Var[str | int] = None


class AppShellMain(MantineLayoutComponentBase):
    """Mantine AppShell.Main."""

    tag = "AppShell.Main"


class AppShellSection(MantineLayoutComponentBase):
    """Mantine AppShell.Section."""

    tag = "AppShell.Section"

    grow: Var[bool] = None


class AppShellRoot(MantineLayoutComponentBase):
    """Mantine AppShell — responsive application layout container.

    https://mantine.dev/core/app-shell/
    """

    tag = "AppShell"

    layout: Var[Literal["default", "alt"]] = None
    mode: Var[Literal["fixed", "static"]] = None
    padding: Var[str | int | dict] = None
    disabled: Var[bool] = None
    offset_scrollbars: Var[bool] = None
    transition_duration: Var[int] = None
    transition_timing_function: Var[str] = None
    with_border: Var[bool] = None
    z_index: Var[str | int] = None
    header: Var[dict] = None
    navbar: Var[dict] = None
    aside: Var[dict] = None
    footer: Var[dict] = None


_APP_SHELL_RESIZABLE_JS = asset(path="app_shell_resizable_wrapper.js", shared=True)


class AppShellResizable(AppShellRoot):
    """Mantine AppShell with resizable sections (Mantine 9.7).

    Wraps ``useAppShellResize`` so sections resize with mouse, touch and
    keyboard. Navbar and Aside resize horizontally, Header and Footer
    vertically. Give the sections a ``width``/``height`` in ``navbar``,
    ``aside``, ``header`` or ``footer`` and enable resizing per section in
    ``resize_options``::

        mn.app_shell.resizable(
            ...,
            navbar={"width": 280, "breakpoint": "sm"},
            resize_options={"navbar": {"min": 200, "max": 480}},
        )

    ``--app-shell-*`` CSS variables are set on the root instead of ``:root``,
    so content in a Portal (Modal, Drawer) cannot read them.

    https://mantine.dev/core/app-shell/
    """

    tag = "AppShellResizable"
    library = _APP_SHELL_RESIZABLE_JS.importable_path
    is_default = True

    lib_dependencies: list[str] = [
        f"{MANTINE_LIBARY}@{MANTINE_VERSION}",
        f"@mantine/hooks@{MANTINE_VERSION}",
    ]

    resize_options: Var[dict] = None
    """Per-section options: ``{"navbar": {"min", "max", "collapseThreshold",
    "label"}, "aside": {...}, "header": {...}, "footer": {...}}``. A section is
    resizable when it has an entry."""

    initial_sizes: Var[dict] = None
    """Sizes applied before the first resize, e.g. ``{"navbar": 320}``."""

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_resize": lambda sizes: [sizes],
            "on_resize_end": lambda sizes: [sizes],
            "on_collapse_change": lambda section, collapsed: [section, collapsed],
        }


class AppShellNamespace(rx.ComponentNamespace):
    """Namespace for AppShell components."""

    __call__ = staticmethod(AppShellRoot.create)
    resizable = staticmethod(AppShellResizable.create)
    header = staticmethod(AppShellHeader.create)
    navbar = staticmethod(AppShellNavbar.create)
    aside = staticmethod(AppShellAside.create)
    footer = staticmethod(AppShellFooter.create)
    main = staticmethod(AppShellMain.create)
    section = staticmethod(AppShellSection.create)


class AspectRatio(MantineLayoutComponentBase):
    """Mantine AspectRatio — maintains width-to-height ratio.

    https://mantine.dev/core/aspect-ratio/
    """

    tag = "AspectRatio"

    ratio: Var[int | float] = None


class Collapse(MantineLayoutComponentBase):
    """Mantine Collapse — animated show/hide container.

    https://mantine.dev/core/collapse/
    """

    tag = "Collapse"

    expanded: Var[bool] = None
    keep_mounted: Var[bool] = None
    animate_opacity: Var[bool] = None
    orientation: Var[Literal["horizontal", "vertical"]] = None
    transition_duration: Var[int] = None
    transition_timing_function: Var[str] = None

    on_transition_start: EventHandler[rx.event.no_args_event_spec] = None
    on_transition_end: EventHandler[rx.event.no_args_event_spec] = None


class FloatingWindow(MantineLayoutComponentBase):
    """Mantine FloatingWindow — draggable, resizable floating element.

    https://mantine.dev/core/floating-window/
    """

    tag = "FloatingWindow"

    enabled: Var[bool] = None
    axis: Var[Literal["x", "y"]] = None
    constrain_to_viewport: Var[bool] = None
    constrain_offset: Var[int] = None
    dimensions: Var[dict] = None
    """Resize constraints (Mantine 9.5): optional px numbers initialWidth,
    minWidth, maxWidth, initialHeight, minHeight, maxHeight."""
    drag_handle_selector: Var[str] = None
    exclude_drag_handle_selector: Var[str] = None
    initial_position: Var[dict] = None
    radius: Var[str | int] = None
    shadow: Var[str] = None
    with_border: Var[bool] = None
    within_portal: Var[bool] = None
    z_index: Var[str | int] = None
    portal_props: Var[dict] = None

    on_drag_start: EventHandler[rx.event.no_args_event_spec] = None
    on_drag_end: EventHandler[rx.event.no_args_event_spec] = None
    on_position_change: EventHandler[lambda pos: [pos]] = None
    on_resize_start: EventHandler[rx.event.no_args_event_spec] = None
    """Called without payload when pointer resize starts (Mantine 9.5)."""
    on_resize_end: EventHandler[rx.event.no_args_event_spec] = None
    """Called without payload when pointer resize ends (Mantine 9.5)."""
    on_size_change: EventHandler[lambda size: [size]] = None
    """Called with the applied ``{width, height}`` on resize (Mantine 9.5)."""


class FloatingWindowResizeHandle(MantineLayoutComponentBase):
    """Mantine FloatingWindow.ResizeHandle — resize grip for FloatingWindow.

    Renders with ``role="separator"``. Keyboard support: Arrow Left/Right
    resize width, Arrow Up/Down resize height in 10px steps; Home/End jump
    to the minimum/maximum size. Respects constrain_to_viewport and
    constrain_offset of the parent FloatingWindow.

    https://mantine.dev/core/floating-window/
    """

    tag = "FloatingWindow.ResizeHandle"

    aria_label: Var[str] = None


class FloatingWindowNamespace(rx.ComponentNamespace):
    """Namespace for FloatingWindow components."""

    __call__ = staticmethod(FloatingWindow.create)
    resize_handle = staticmethod(FloatingWindowResizeHandle.create)


class Marquee(MantineLayoutComponentBase):
    """Mantine Marquee — continuously scrolling content.

    https://mantine.dev/core/marquee/
    """

    tag = "Marquee"

    duration: Var[int | float] = None
    gap: Var[str | int] = None
    orientation: Var[Literal["horizontal", "vertical"]] = None
    pause_on_hover: Var[bool] = None
    repeat: Var[int] = None
    reverse: Var[bool] = None
    fade_edges: Var[bool] = None
    fade_edge_color: Var[str] = None
    fade_edge_size: Var[str] = None


class OverflowList(MantineLayoutComponentBase):
    """Mantine OverflowList — shows visible items and collapses the rest.

    https://mantine.dev/core/overflow-list/
    """

    tag = "OverflowList"

    data: Var[list[Any]] = None
    gap: Var[str | int] = None
    max_rows: Var[int] = None
    max_visible_items: Var[int] = None
    render_item: Var[Any] = None
    render_overflow: Var[Any] = None
    collapse_from: Var[Literal["start", "end"]] = None
    """Direction from which items collapse when overflowing (Mantine 9.3)."""


class Portal(MantineComponentBase):
    """Mantine Portal — renders children in a different DOM location.

    https://mantine.dev/core/portal/
    """

    tag = "Portal"

    target: Var[str] = None
    reuse_target_node: Var[bool] = None


class RollingNumber(MantineLayoutComponentBase):
    """Mantine RollingNumber — animated number with rolling digits.

    https://mantine.dev/core/rolling-number/
    """

    tag = "RollingNumber"

    value: Var[int | float] = None
    animation_duration: Var[int] = None
    timing_function: Var[str] = None
    decimal_scale: Var[int] = None
    decimal_separator: Var[str] = None
    fixed_decimal_scale: Var[bool] = None
    thousand_separator: Var[str | bool] = None
    prefix: Var[str] = None
    suffix: Var[str] = None
    tabular_numbers: Var[bool] = None
    with_live_region: Var[bool] = None


class Scroller(MantineLayoutComponentBase):
    """Mantine Scroller — horizontal scroll container with navigation.

    https://mantine.dev/core/scroller/
    """

    tag = "Scroller"

    draggable: Var[bool] = None
    scroll_amount: Var[int] = None
    control_size: Var[str | int] = None
    edge_gradient_color: Var[str] = None
    show_start_control: Var[bool] = None
    show_end_control: Var[bool] = None
    start_control_icon: Var[Any] = None
    end_control_icon: Var[Any] = None


class Transition(MantineComponentBase):
    """Mantine Transition — animated mount/unmount wrapper.

    https://mantine.dev/core/transition/
    """

    tag = "Transition"

    mounted: Var[bool] = None
    transition: Var[str | dict] = None
    duration: Var[int] = None
    exit_duration: Var[int] = None
    enter_delay: Var[int] = None
    exit_delay: Var[int] = None
    timing_function: Var[str] = None
    keep_mounted: Var[bool] = None

    on_enter: EventHandler[rx.event.no_args_event_spec] = None
    on_entered: EventHandler[rx.event.no_args_event_spec] = None
    on_exit: EventHandler[rx.event.no_args_event_spec] = None
    on_exited: EventHandler[rx.event.no_args_event_spec] = None


class VisuallyHidden(MantineLayoutComponentBase):
    """Mantine VisuallyHidden — hides content visually but keeps it accessible.

    https://mantine.dev/core/visually-hidden/
    """

    tag = "VisuallyHidden"


app_shell = AppShellNamespace()
aspect_ratio = AspectRatio.create
box = Box.create
center = Center.create
collapse = Collapse.create
container = Container.create
flex = Flex.create
floating_window = FloatingWindowNamespace()
group = Group.create
marquee = Marquee.create
overflow_list = OverflowList.create
portal = Portal.create
rolling_number = RollingNumber.create
scroller = Scroller.create
simple_grid = SimpleGrid.create
stack = Stack.create
grid = Grid.create
grid_col = GridCol.create
space = Space.create
divider = Divider.create
affix = Affix.create
focus_trap = FocusTrap.create
transition = Transition.create
visually_hidden = VisuallyHidden.create
