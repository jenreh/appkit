"""Mantine data display components."""

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineInputComponentBase, MantineLayoutComponentBase


class Accordion(MantineLayoutComponentBase):
    """Mantine Accordion component."""

    tag = "Accordion"

    multiple: Var[bool]
    value: Var[str | list[str]]
    default_value: Var[str | list[str]]
    transition_duration: Var[int]
    disable_chevron_rotation: Var[bool]
    chevron_position: Var[Literal["left", "right"]]
    chevron: Var[Any]
    order: Var[int]
    variant: Var[str]  # default, contained, filled, separated
    radius: Var[str | int]

    on_change: EventHandler[lambda value: [value]]


class AccordionItem(MantineLayoutComponentBase):
    """Mantine Accordion.Item component."""

    tag = "Accordion.Item"

    value: Var[str]


class AccordionControl(MantineLayoutComponentBase):
    """Mantine Accordion.Control component."""

    tag = "Accordion.Control"

    disabled: Var[bool]
    chevron: Var[Any]
    icon: Var[Any]


class AccordionPanel(MantineLayoutComponentBase):
    """Mantine Accordion.Panel component."""

    tag = "Accordion.Panel"


class Avatar(MantineLayoutComponentBase):
    """Mantine Avatar component."""

    tag = "Avatar"

    src: Var[str]
    alt: Var[str]
    radius: Var[str | int]
    size: Var[str | int]
    color: Var[str]
    variant: Var[str]  # filled, light, outline, transparent, white, default
    name: Var[str]
    allowed_initials_colors: Var[list[str]]


class AvatarGroup(MantineLayoutComponentBase):
    """Mantine Avatar.Group component."""

    tag = "Avatar.Group"

    spacing: Var[str | int]


class Card(MantineLayoutComponentBase):
    """Mantine Card component."""

    tag = "Card"

    shadow: Var[str]
    radius: Var[str | int]
    with_border: Var[bool]
    padding: Var[str | int]


class CardSection(MantineLayoutComponentBase):
    """Mantine Card.Section component."""

    tag = "Card.Section"

    with_border: Var[bool]
    inherit_padding: Var[bool]


class Image(MantineLayoutComponentBase):
    """Mantine Image component."""

    tag = "Image"

    src: Var[str]
    fit: Var[Literal["cover", "contain", "fill", "none", "scale-down"]]
    fallback_src: Var[str]
    radius: Var[str | int]
    w: Var[str | int]
    h: Var[str | int]


class Paper(MantineLayoutComponentBase):
    """Mantine Paper component."""

    tag = "Paper"

    shadow: Var[str]
    radius: Var[str | int]
    with_border: Var[bool]


class Indicator(MantineLayoutComponentBase):
    """Mantine Indicator component."""

    tag = "Indicator"

    position: Var[str]
    offset: Var[int]
    inline: Var[bool]
    size: Var[str | int]
    color: Var[str]
    with_border: Var[bool]
    disabled: Var[bool]
    processing: Var[bool]
    z_index: Var[int | str]
    label: Var[str | Any]


class Timeline(MantineLayoutComponentBase):
    """Mantine Timeline component."""

    tag = "Timeline"

    active: Var[int]
    reverse_active: Var[bool]
    line_width: Var[int]
    bullet_size: Var[int]
    color: Var[str]
    radius: Var[str | int]
    align: Var[Literal["right", "left"]]


class TimelineItem(MantineLayoutComponentBase):
    """Mantine Timeline.Item component."""

    tag = "Timeline.Item"

    title: Var[str]
    bullet: Var[Any]
    bullet_size: Var[int]
    radius: Var[str | int]
    color: Var[str]
    line_variant: Var[Literal["solid", "dashed", "dotted"]]


class NumberFormatter(MantineInputComponentBase):
    """Mantine NumberFormatter wrapper for Reflex.

    See: https://mantine.dev/core/number-formatter/

    This component formats numeric input according to provided parser/formatter
    and exposes on_change receiving the parsed value.
    """

    tag = "NumberFormatter"
    alias = "MantineNumberFormatter"

    # Formatting/parser behavior
    allow_negative: Var[bool] = True
    decimal_scale: Var[int] = None
    decimal_separator: Var[str] = "."
    fixed_decimal_scale: Var[bool] = False
    prefix: Var[str] = None
    suffix: Var[str] = None
    thousand_separator: Var[str | bool] = ","
    thousands_group_style: Var[Literal["thousand", "lakh", "wan", "none"]] = "none"


#### Factory functions for easier imports and usage


class AccordionNamespace(rx.ComponentNamespace):
    """Namespace for Accordion components."""

    __call__ = staticmethod(Accordion.create)
    item = staticmethod(AccordionItem.create)
    control = staticmethod(AccordionControl.create)
    panel = staticmethod(AccordionPanel.create)


class AvatarNamespace(rx.ComponentNamespace):
    """Namespace for Avatar components."""

    __call__ = staticmethod(Avatar.create)
    group = staticmethod(AvatarGroup.create)


class CardNamespace(rx.ComponentNamespace):
    """Namespace for Card components."""

    __call__ = staticmethod(Card.create)
    section = staticmethod(CardSection.create)


class TimelineNamespace(rx.ComponentNamespace):
    """Namespace for Timeline components."""

    __call__ = staticmethod(Timeline.create)
    item = staticmethod(TimelineItem.create)


accordion = AccordionNamespace()
avatar = AvatarNamespace()
card = CardNamespace()
image = Image.create
indicator = Indicator.create
number_formatter = NumberFormatter.create
paper = Paper.create
timeline = TimelineNamespace()
