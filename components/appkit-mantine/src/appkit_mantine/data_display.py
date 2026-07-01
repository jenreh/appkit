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


class Badge(MantineLayoutComponentBase):
    """Mantine Badge component."""

    tag = "Badge"

    auto_contrast: Var[bool]
    circle: Var[bool]
    color: Var[str]
    full_width: Var[bool]
    gradient: Var[dict[str, Any]]
    left_section: Var[Any]
    radius: Var[str | int]
    right_section: Var[Any]
    size: Var[str | int]
    variant: Var[str]  # filled, light, outline, dot, transparent, default, white


class Card(MantineLayoutComponentBase):
    """Mantine Card component."""

    tag = "Card"

    shadow: Var[str]
    radius: Var[str | int]
    with_border: Var[bool]
    padding: Var[str | int]
    orientation: Var[Literal["horizontal", "vertical"]]


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


class Kbd(MantineLayoutComponentBase):
    """Mantine Kbd component — keyboard key display.

    https://mantine.dev/core/kbd/
    """

    tag = "Kbd"

    size: Var[str | int] = None


class ColorSwatch(MantineLayoutComponentBase):
    """Mantine ColorSwatch component — displays a color sample.

    https://mantine.dev/core/color-swatch/
    """

    tag = "ColorSwatch"

    _rename_props = {
        "with_shadow": "withShadow",
    }

    color: Var[str] = None
    radius: Var[str | int] = None
    size: Var[str | int] = None
    with_shadow: Var[bool] = None


class ThemeIcon(MantineLayoutComponentBase):
    """Mantine ThemeIcon component — colored icon container.

    https://mantine.dev/core/theme-icon/
    """

    tag = "ThemeIcon"

    _rename_props = {
        "auto_contrast": "autoContrast",
    }

    color: Var[str] = None
    gradient: Var[dict] = None
    radius: Var[str | int] = None
    size: Var[str | int] = None
    variant: Var[str] = None
    auto_contrast: Var[bool] = None


class Spoiler(MantineLayoutComponentBase):
    """Mantine Spoiler component — expandable content with show/hide toggle.

    https://mantine.dev/core/spoiler/
    """

    tag = "Spoiler"

    _rename_props = {
        "default_expanded": "defaultExpanded",
        "hide_label": "hideLabel",
        "hide_aria_label": "hideAriaLabel",
        "max_height": "maxHeight",
        "show_label": "showLabel",
        "show_aria_label": "showAriaLabel",
        "transition_duration": "transitionDuration",
    }

    show_label: Var[Any] = None
    """Label for the show more button (required)."""

    hide_label: Var[Any] = None
    """Label for the hide button (required)."""

    max_height: Var[int] = None
    default_expanded: Var[bool] = None
    expanded: Var[bool] = None
    transition_duration: Var[int] = None
    show_aria_label: Var[str] = None
    hide_aria_label: Var[str] = None

    on_expanded_change: EventHandler[lambda expanded: [expanded]] = None


class BackgroundImage(MantineLayoutComponentBase):
    """Mantine BackgroundImage component — div with background image.

    https://mantine.dev/core/background-image/
    """

    tag = "BackgroundImage"

    src: Var[str] = None
    radius: Var[str | int] = None


class DataList(MantineLayoutComponentBase):
    """Mantine DataList — semantic label/value pairs (``dl``/``dt``/``dd``).

    https://mantine.dev/core/data-list/ (Mantine 9.4)
    """

    tag = "DataList"

    gap: Var[str | int] = None
    label_width: Var[str | int] = None
    orientation: Var[Literal["horizontal", "vertical"]] = None
    size: Var[str | int] = None
    with_divider: Var[bool] = None


class DataListItem(MantineLayoutComponentBase):
    """Mantine DataList.Item — a single label/value pair."""

    tag = "DataList.Item"


class DataListItemLabel(MantineLayoutComponentBase):
    """Mantine DataList.ItemLabel — the ``dt`` label element."""

    tag = "DataList.ItemLabel"


class DataListItemValue(MantineLayoutComponentBase):
    """Mantine DataList.ItemValue — the ``dd`` value element."""

    tag = "DataList.ItemValue"


class EmptyState(MantineLayoutComponentBase):
    """Mantine EmptyState — placeholder for "no data" situations.

    https://mantine.dev/core/empty-state/ (Mantine 9.4)
    """

    tag = "EmptyState"

    align: Var[Literal["center", "left", "right"]] = None
    color: Var[str] = None
    description: Var[Any] = None
    icon: Var[Any] = None
    size: Var[str | int] = None
    title: Var[Any] = None
    with_indicator_background: Var[bool] = None
    variant: Var[Literal["filled", "light"]] = None


class EmptyStateIndicator(MantineLayoutComponentBase):
    """Mantine EmptyState.Indicator — icon/illustration wrapper."""

    tag = "EmptyState.Indicator"


class EmptyStateTitle(MantineLayoutComponentBase):
    """Mantine EmptyState.Title — title element."""

    tag = "EmptyState.Title"


class EmptyStateDescription(MantineLayoutComponentBase):
    """Mantine EmptyState.Description — description text wrapper."""

    tag = "EmptyState.Description"


class EmptyStateActions(MantineLayoutComponentBase):
    """Mantine EmptyState.Actions — action buttons container."""

    tag = "EmptyState.Actions"


#### Factory functions for easier imports and usage


class DataListNamespace(rx.ComponentNamespace):
    """Namespace for DataList components."""

    __call__ = staticmethod(DataList.create)
    item = staticmethod(DataListItem.create)
    item_label = staticmethod(DataListItemLabel.create)
    item_value = staticmethod(DataListItemValue.create)


class EmptyStateNamespace(rx.ComponentNamespace):
    """Namespace for EmptyState components."""

    __call__ = staticmethod(EmptyState.create)
    indicator = staticmethod(EmptyStateIndicator.create)
    title = staticmethod(EmptyStateTitle.create)
    description = staticmethod(EmptyStateDescription.create)
    actions = staticmethod(EmptyStateActions.create)


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
background_image = BackgroundImage.create
badge = Badge.create
card = CardNamespace()
color_swatch = ColorSwatch.create
data_list = DataListNamespace()
empty_state = EmptyStateNamespace()
image = Image.create
indicator = Indicator.create
kbd = Kbd.create
number_formatter = NumberFormatter.create
paper = Paper.create
spoiler = Spoiler.create
theme_icon = ThemeIcon.create
timeline = TimelineNamespace()
