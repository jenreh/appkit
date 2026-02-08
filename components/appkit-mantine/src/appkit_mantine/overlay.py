"""Mantine overlay components."""

from typing import Any

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineLayoutComponentBase


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
