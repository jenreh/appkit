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
            target_var = rx.Var.create(
                f"document.getElementById({FloatingIndicatorState.active_id})",
                _var_is_local=False,
                _var_is_string=False,
            )
            parent_var = rx.Var.create(
                "document.getElementById('parent-container')",
                _var_is_local=False,
                _var_is_string=False,
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


class HoverCardNamespace(rx.ComponentNamespace):
    """Namespace for HoverCard components."""

    __call__ = staticmethod(HoverCard.create)
    target = staticmethod(HoverCardTarget.create)
    dropdown = staticmethod(HoverCardDropdown.create)


class TooltipNamespace(rx.ComponentNamespace):
    """Namespace for Tooltip components."""

    __call__ = staticmethod(Tooltip.create)
    floating = staticmethod(TooltipFloating.create)


hover_card = HoverCardNamespace()
tooltip = TooltipNamespace()
overlay = Overlay.create
loading_overlay = LoadingOverlay.create
floating_indicator = FloatingIndicator.create
