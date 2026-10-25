"""Mantine numeric inputs: NumberInput, Rating, and AngleSlider."""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MantineInputComponentBase, MantineLayoutComponentBase


class NumberInput(MantineInputComponentBase):
    """Mantine NumberInput component for numeric input with controls.

    Based on: https://mantine.dev/core/number-input/

    Inherits common input props from MantineInputComponentBase.
    See `mantine_number_input()` function for detailed documentation and examples.
    """

    tag = "NumberInput"
    alias = "MantineNumberInput"

    # Prop aliasing for camelCase React props

    # Numeric constraints
    min: Var[int | float] = None
    """Minimum allowed value."""

    max: Var[int | float] = None
    """Maximum allowed value."""

    step: Var[int | float] = None
    """Step for increment/decrement (default: 1)."""

    clamp_behavior: Var[Literal["strict", "blur", "none"]] = None
    """Value clamping behavior: strict (clamp on input), blur (clamp on blur),
    none (no clamping)."""

    # Decimal handling
    decimal_scale: Var[int] = None
    """Maximum number of decimal places."""

    fixed_decimal_scale: Var[bool] = None
    """Pad decimals with zeros to match decimal_scale."""

    decimal_separator: Var[str] = None
    """Decimal separator character (default: ".")."""

    allowed_decimal_separators: Var[list[str]] = None
    """Characters which when pressed result in a decimal separator
    (default: ['.', ','])."""

    allow_decimal: Var[bool] = None
    """Allow decimal input (default: True)."""

    # Zero formatting
    allow_leading_zeros: Var[bool] = None
    """Determines whether leading zeros are allowed during input (default: True)."""

    trim_leading_zeroes_on_blur: Var[bool] = None
    """If set, leading zeros are removed on blur (default: True)."""

    # Number formatting
    allow_negative: Var[bool] = None
    """Allow negative numbers (default: True)."""

    prefix: Var[str] = None
    """Text prefix (e.g., "$")."""

    suffix: Var[str] = None
    """Text suffix (e.g., "%")."""

    thousand_separator: Var[str | bool] = None
    """Thousand separator character or True for locale default."""

    thousands_group_style: Var[Literal["thousand", "lakh", "wan", "none"]] = None
    """Grouping style: thousand (1,000,000), lakh (1,00,000), wan (1,0000),
    none (no grouping)."""

    value_is_numeric_string: Var[bool] = None
    """Advanced: Set to true if passing numeric strings and using formatting
    props like prefix or suffix."""

    select_all_on_focus: Var[bool] = None
    """If set, all text is selected when the input receives focus (default: False)."""

    # Controls
    hide_controls: Var[bool] = None
    """Hide increment/decrement buttons."""

    start_value: Var[int | float] = None
    """Value when empty input is focused (default: 0)."""

    step_hold_delay: Var[int] = None
    """Initial delay in milliseconds before stepping the value."""

    step_hold_interval: Var[int] = None
    """Interval in milliseconds between value steps when increment/decrement
    button is held down."""

    with_keyboard_events: Var[bool] = None
    """Enable up/down keyboard events for incrementing/decrementing (default: True).

    When True, pressing up/down arrow keys while focused increments/decrements
    the value by the step amount. Essential for keyboard-based navigation."""

    allow_mouse_wheel: Var[bool] = None
    """Enable mouse wheel increments/decrements (default: False)."""

    on_max_reached: EventHandler[rx.event.no_args_event_spec] = None
    """Called when the decrement button or arrow down key is pressed and
    the value has reached the minimum."""

    on_min_reached: EventHandler[rx.event.no_args_event_spec] = None
    """Called when the increment button or arrow up key is pressed and
    the value has reached the maximum."""

    on_value_change: EventHandler[rx.event.input_event] = None
    """Called when value changes with react-number-format payload."""

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        """Override event triggers to handle NumberInput value emission.

        Mantine NumberInput sends the numeric value directly (or empty string),
        not an event object like standard input. The up/down arrow controls and
        keyboard events (up/down keys) depend on proper value transformation
        for Reflex state compatibility.

        References:
        - https://mantine.dev/core/number-input/?t=props (see withKeyboardEvents)
        - NumberInput extends react-number-format NumericFormat component
        - Increment/decrement controls automatically use onChange when step occurs
        """

        def _on_change(value: Var) -> list[Var]:
            # Mantine NumberInput sends value directly (number or empty string)
            # Forward it as-is to Reflex state
            return [value]

        return {
            **super().get_event_triggers(),
            "on_change": _on_change,
        }


class Rating(MantineLayoutComponentBase):
    """Mantine Rating component — star/symbol rating input.

    https://mantine.dev/core/rating/
    """

    tag = "Rating"

    value: Var[int | float] = None
    default_value: Var[int | float] = None
    count: Var[int] = None
    fractions: Var[int] = None
    color: Var[str] = None
    size: Var[str | int] = None
    name: Var[str] = None
    read_only: Var[bool] = None
    allow_clear: Var[bool] = None
    highlight_selected_only: Var[bool] = None
    empty_symbol: Var[Any] = None
    full_symbol: Var[Any] = None

    on_change: EventHandler[lambda value: [value]] = None
    on_hover: EventHandler[lambda value: [value]] = None


class AngleSlider(MantineLayoutComponentBase):
    """Mantine AngleSlider component — circular angle input slider.

    https://mantine.dev/core/angle-slider/
    """

    tag = "AngleSlider"

    value: Var[int | float] = None
    default_value: Var[int | float] = None
    step: Var[int] = None
    size: Var[int] = None
    thumb_size: Var[int] = None
    disabled: Var[bool] = None
    with_label: Var[bool] = None
    restrict_to_marks: Var[bool] = None
    marks: Var[list[dict]] = None
    name: Var[str] = None
    format_label: Var[Any] = None
    """JS function ``(value) => ReactNode`` that formats the label."""

    on_change: EventHandler[lambda value: [value]] = None
    on_change_end: EventHandler[lambda value: [value]] = None
    on_scrub_start: EventHandler[rx.event.no_args_event_spec] = None
    on_scrub_end: EventHandler[rx.event.no_args_event_spec] = None
