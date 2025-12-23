"""Mantine Slider component for Reflex."""

from collections.abc import Callable
from typing import Any

import reflex as rx
from reflex.vars import Var


class Slider(rx.Component):
    """Mantine Slider component - interactive input for selecting numeric values."""

    library = "@mantine/core"
    tag = "Slider"

    # Value props
    value: Var[int | float]
    default_value: Var[int | float]
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
    thumb_children: Var[Any]
    thumb_label: Var[str]

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

    # Layout
    w: Var[str | int]
    m: Var[str | int]
    mt: Var[str | int]
    mb: Var[str | int]
    ml: Var[str | int]
    mr: Var[str | int]
    mx: Var[str | int]
    my: Var[str | int]
    p: Var[str | int]
    pt: Var[str | int]
    pb: Var[str | int]
    pl: Var[str | int]
    pr: Var[str | int]
    px: Var[str | int]
    py: Var[str | int]

    def _get_imports(self) -> dict[str, list[str]]:
        return {"@mantine/core": ["Slider"]}

    def _rename_props(self) -> dict[str, str]:
        return {
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
            "thumb_label": "thumbLabel",
            "thumb_size": "thumbSize",
        }


class RangeSlider(rx.Component):
    """Mantine RangeSlider component - interactive input for selecting numeric ranges."""

    library = "@mantine/core"
    tag = "RangeSlider"

    # Value props (range uses list of two values)
    value: Var[list[int | float]]
    default_value: Var[list[int | float]]
    on_change: rx.EventHandler[lambda value: [value]]
    on_change_end: rx.EventHandler[lambda value: [value]]

    # Range props
    min: Var[int | float]
    max: Var[int | float]
    step: Var[int | float]
    domain: Var[list[int | float]]
    min_range: Var[int | float]
    max_range: Var[int | float]

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
    thumb_children: Var[list[Any]]
    thumb_from_label: Var[str]
    thumb_to_label: Var[str]

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

    # Layout
    w: Var[str | int]
    m: Var[str | int]
    mt: Var[str | int]
    mb: Var[str | int]
    ml: Var[str | int]
    mr: Var[str | int]
    mx: Var[str | int]
    my: Var[str | int]
    p: Var[str | int]
    pt: Var[str | int]
    pb: Var[str | int]
    pl: Var[str | int]
    pr: Var[str | int]
    px: Var[str | int]
    py: Var[str | int]

    def _get_imports(self) -> dict[str, list[str]]:
        return {"@mantine/core": ["RangeSlider"]}

    def _rename_props(self) -> dict[str, str]:
        return {
            "class_name": "className",
            "class_names": "classNames",
            "default_value": "defaultValue",
            "label_always_on": "labelAlwaysOn",
            "label_transition_props": "labelTransitionProps",
            "max_range": "maxRange",
            "min_range": "minRange",
            "on_change_end": "onChangeEnd",
            "on_change": "onChange",
            "restrict_to_marks": "restrictToMarks",
            "show_label_on_hover": "showLabelOnHover",
            "thumb_children": "thumbChildren",
            "thumb_from_label": "thumbFromLabel",
            "thumb_size": "thumbSize",
            "thumb_to_label": "thumbToLabel",
        }


# Convenience functions
slider = Slider.create
range_slider = RangeSlider.create
