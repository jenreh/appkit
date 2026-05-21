"""Mantine overlay components."""

from typing import Any

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineLayoutComponentBase


class Overlay(MantineLayoutComponentBase):
    """Mantine Overlay component."""

    tag = "Overlay"

    color: Var[str]
    background_opacity: Var[float]
    blur: Var[int | float]
    gradient: Var[str]
    z_index: Var[int | str]


class LoadingOverlay(MantineLayoutComponentBase):
    """Mantine LoadingOverlay component."""

    tag = "LoadingOverlay"

    visible: Var[bool]
    z_index: Var[int | str]
    loader_props: Var[dict[str, Any]]
    overlay_props: Var[dict[str, Any]]
    label: Var[str]


class HoverCard(MantineLayoutComponentBase):
    """Mantine HoverCard component."""

    tag = "HoverCard"

    width: Var[str | int]
    shadow: Var[str]
    open_delay: Var[int]
    close_delay: Var[int]
    keep_mounted: Var[bool]
    disabled: Var[bool]
    initially_opened: Var[bool]

    on_open: EventHandler[list]
    on_close: EventHandler[list]


class HoverCardTarget(MantineLayoutComponentBase):
    """Mantine HoverCard.Target component."""

    tag = "HoverCard.Target"


class HoverCardDropdown(MantineLayoutComponentBase):
    """Mantine HoverCard.Dropdown component."""

    tag = "HoverCard.Dropdown"


class Tooltip(MantineLayoutComponentBase):
    """Mantine Tooltip component."""

    tag = "Tooltip"

    label: Var[str | Any]
    position: Var[str]
    offset: Var[int]
    open_delay: Var[int]
    close_delay: Var[int]
    color: Var[str]
    radius: Var[str | int]
    arrow_size: Var[int]
    arrow_offset: Var[int]
    arrow_radius: Var[int]
    arrow_position: Var[str]
    with_arrow: Var[bool]
    opened: Var[bool]
    z_index: Var[int | str]
    events: Var[dict]
    transition_props: Var[dict]
    multiline: Var[bool]
    inline: Var[bool]


class TooltipFloating(MantineLayoutComponentBase):
    """Mantine Tooltip.Floating component."""

    tag = "Tooltip.Floating"

    label: Var[str | Any]
    position: Var[str]
    offset: Var[int]
    color: Var[str]
    radius: Var[str | int]
    z_index: Var[int | str]
    multiline: Var[bool]


class FloatingIndicator(MantineLayoutComponentBase):
    """Mantine FloatingIndicator component.

    Display a floating indicator over a group of elements.

    Example:
        ```python
        import reflex as rx
        import appkit_mantine as mn


        class FloatingIndicatorState(rx.State):
            active_id: str = "btn1"

            def set_active(self, selected_id: str):
                self.active_id = selected_id


        def floating_indicator_example():
            target_var = rx.Var(
                _js_expr=f"document.getElementById({FloatingIndicatorState.active_id})",
            )
            parent_var = rx.Var(
                _js_expr="document.getElementById('parent-container')",
            )

            return rx.box(
                mn.group(
                    mn.button(
                        "React",
                        id="btn1",
                        on_click=FloatingIndicatorState.set_active("btn1"),
                    ),
                    mn.button(
                        "Vue",
                        id="btn2",
                        on_click=FloatingIndicatorState.set_active("btn2"),
                    ),
                    mn.button(
                        "Angular",
                        id="btn3",
                        on_click=FloatingIndicatorState.set_active("btn3"),
                    ),
                ),
                mn.floating_indicator(
                    parent=parent_var,
                    target=target_var,
                    transition_duration=150,
                ),
                id="parent-container",
                pos="relative",
                bg="gray.1",
                p="md",
            )
        ```
    """

    tag = "FloatingIndicator"

    target: Var[Any]
    """Target element over which the indicator is displayed."""

    parent: Var[Any]
    """Parent container element that must have position: relative."""

    display_after_transition_end: Var[bool]
    """Controls whether the indicator should be hidden initially and displayed
    after the parent's transition ends."""

    transition_duration: Var[int | str]
    """Transition duration in ms."""

    on_transition_end: EventHandler[rx.event.no_args_event_spec]
    """Called when the indicator finishes transitioning to a new position."""

    on_transition_start: EventHandler[rx.event.no_args_event_spec]
    """Called when the indicator starts transitioning to a new position."""


class PopoverRoot(MantineLayoutComponentBase):
    """Mantine Popover — floating content panel anchored to a trigger.

    https://mantine.dev/core/popover/
    """

    tag = "Popover"

    _rename_props = {
        "arrow_offset": "arrowOffset",
        "arrow_position": "arrowPosition",
        "arrow_radius": "arrowRadius",
        "arrow_size": "arrowSize",
        "close_on_click_outside": "closeOnClickOutside",
        "close_on_escape": "closeOnEscape",
        "default_opened": "defaultOpened",
        "keep_mounted": "keepMounted",
        "return_focus": "returnFocus",
        "trap_focus": "trapFocus",
        "with_arrow": "withArrow",
        "with_overlay": "withOverlay",
        "within_portal": "withinPortal",
    }

    opened: Var[bool] = None
    default_opened: Var[bool] = None
    position: Var[str] = None
    offset: Var[int | dict] = None
    width: Var[str | int] = None
    with_arrow: Var[bool] = None
    with_overlay: Var[bool] = None
    arrow_size: Var[int] = None
    arrow_offset: Var[int] = None
    arrow_radius: Var[int] = None
    arrow_position: Var[str] = None
    shadow: Var[str] = None
    radius: Var[str | int] = None
    z_index: Var[str | int] = None
    trap_focus: Var[bool] = None
    return_focus: Var[bool] = None
    keep_mounted: Var[bool] = None
    close_on_click_outside: Var[bool] = None
    close_on_escape: Var[bool] = None
    within_portal: Var[bool] = None
    disabled: Var[bool] = None

    on_open: EventHandler[rx.event.no_args_event_spec] = None
    on_close: EventHandler[rx.event.no_args_event_spec] = None
    on_dismiss: EventHandler[rx.event.no_args_event_spec] = None
    on_change: EventHandler[lambda opened: [opened]] = None


class PopoverTarget(MantineLayoutComponentBase):
    """Mantine Popover.Target — the trigger element."""

    tag = "Popover.Target"

    popup_type: Var[str] = None
    ref_prop: Var[str] = None


class PopoverDropdown(MantineLayoutComponentBase):
    """Mantine Popover.Dropdown — the floating content panel."""

    tag = "Popover.Dropdown"


class PopoverNamespace(rx.ComponentNamespace):
    """Namespace for Popover components."""

    __call__ = staticmethod(PopoverRoot.create)
    target = staticmethod(PopoverTarget.create)
    dropdown = staticmethod(PopoverDropdown.create)


class Dialog(MantineLayoutComponentBase):
    """Mantine Dialog — small floating dialog panel.

    https://mantine.dev/core/dialog/
    """

    tag = "Dialog"

    _rename_props = {
        "keep_mounted": "keepMounted",
        "on_close": "onClose",
        "portal_props": "portalProps",
        "transition_props": "transitionProps",
        "with_border": "withBorder",
        "with_close_button": "withCloseButton",
        "within_portal": "withinPortal",
        "z_index": "zIndex",
    }

    opened: Var[bool] = None
    position: Var[dict] = None
    radius: Var[str | int] = None
    shadow: Var[str] = None
    size: Var[str | int] = None
    keep_mounted: Var[bool] = None
    with_border: Var[bool] = None
    with_close_button: Var[bool] = None
    within_portal: Var[bool] = None
    z_index: Var[str | int] = None
    transition_props: Var[dict] = None
    portal_props: Var[dict] = None

    on_close: EventHandler[rx.event.no_args_event_spec] = None


class HoverCardNamespace(rx.ComponentNamespace):
    """Namespace for HoverCard components."""

    __call__ = staticmethod(HoverCard.create)
    target = staticmethod(HoverCardTarget.create)
    dropdown = staticmethod(HoverCardDropdown.create)


class TooltipNamespace(rx.ComponentNamespace):
    """Namespace for Tooltip components."""

    __call__ = staticmethod(Tooltip.create)
    floating = staticmethod(TooltipFloating.create)


popover = PopoverNamespace()
dialog = Dialog.create
hover_card = HoverCardNamespace()
tooltip = TooltipNamespace()
overlay = Overlay.create
loading_overlay = LoadingOverlay.create
floating_indicator = FloatingIndicator.create
