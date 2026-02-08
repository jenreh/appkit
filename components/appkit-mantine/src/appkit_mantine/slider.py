"""Mantine Slider component for Reflex."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import reflex as rx
from reflex.vars import Var

from appkit_mantine.base import MantineLayoutComponentBase


class MantineSliderBase(MantineLayoutComponentBase):
    """Base class for Slider and RangeSlider."""

    # Event handlers
    on_change: rx.EventHandler[lambda value: [value]]
    on_change_end: rx.EventHandler[lambda value: [value]]

    # Range props
    min: Var[int | float]
    max: Var[int | float]
    step: Var[int | float]
    domain: Var[list[int | float]]

    # Label props
    label: Var[Callable | str | None]
    label_always_on: Var[bool]
    label_transition_props: Var[dict[str, Any]]

    # Marks
    marks: Var[list[dict[str, Any]]]
    restrict_to_marks: Var[bool]

    # Appearance
    color: Var[str]
    size: Var[str | int]
    radius: Var[str | int]
    thumb_size: Var[int]

    # Behavior
    disabled: Var[bool]
    inverted: Var[bool]
    scale: Var[Callable]
    show_label_on_hover: Var[bool]

    # Style props
    class_name: Var[str]
    class_names: Var[dict[str, str]]
    styles: Var[dict[str, Any]]
    unstyled: Var[bool]

    _rename_props = {
        "class_name": "className",
        "class_names": "classNames",
        "default_value": "defaultValue",
        "label_always_on": "labelAlwaysOn",
        "label_transition_props": "labelTransitionProps",
        "on_change_end": "onChangeEnd",
        "on_change": "onChange",
        "restrict_to_marks": "restrictToMarks",
        "show_label_on_hover": "showLabelOnHover",
        "thumb_children": "thumbChildren",
        "thumb_size": "thumbSize",
    }


class Slider(MantineSliderBase):
    """Mantine Slider component - interactive input for selecting numeric values."""

    tag = "Slider"

    # Value props
    value: Var[int | float]
    default_value: Var[int | float]

    # Appearance
    thumb_children: Var[Any]
    thumb_label: Var[str]

    _rename_props = {
        **MantineSliderBase._rename_props,  # noqa: SLF001
        "thumb_label": "thumbLabel",
    }


class RangeSlider(MantineSliderBase):
    """Mantine RangeSlider component - interactive input for selecting
    numeric ranges."""

    tag = "RangeSlider"

    # Value props (range uses list of two values)
    value: Var[list[int | float]]
    default_value: Var[list[int | float]]

    # Appearance
    thumb_children: Var[list[Any]]
    thumb_from_label: Var[str]
    thumb_to_label: Var[str]

    # Range props
    min_range: Var[int | float]
    max_range: Var[int | float]

    _rename_props = {
        **MantineSliderBase._rename_props,  # noqa: SLF001
        "thumb_from_label": "thumbFromLabel",
        "thumb_to_label": "thumbToLabel",
        "max_range": "maxRange",
        "min_range": "minRange",
    }


# Convenience functions
slider = Slider.create
range_slider = RangeSlider.create
