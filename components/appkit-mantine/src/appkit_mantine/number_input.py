"""Mantine NumberInput component wrapper for Reflex.

Provides numeric input with validation, formatting, and increment/decrement controls.
See `mantine_number_input()` function for detailed usage and examples.

Documentation: https://mantine.dev/core/number-input/
"""

from __future__ import annotations

from typing import Any, Literal

from reflex.vars.base import Var

from appkit_mantine.base import (
    MantineInputComponentBase,
)


class NumberInput(MantineInputComponentBase):
    """Mantine NumberInput component for numeric input with controls.

    Based on: https://mantine.dev/core/number-input/

    Inherits common input props from MantineInputComponentBase.
    See `mantine_number_input()` function for detailed documentation and examples.
    """

    tag = "NumberInput"
    alias = "MantineNumberInput"

    # Prop aliasing for camelCase React props
    _rename_props = {
        **MantineInputComponentBase._rename_props,  # noqa: SLF001
        "clamp_behavior": "clampBehavior",
        "decimal_scale": "decimalScale",
        "fixed_decimal_scale": "fixedDecimalScale",
        "decimal_separator": "decimalSeparator",
        "allow_decimal": "allowDecimal",
        "allow_negative": "allowNegative",
        "thousand_separator": "thousandSeparator",
        "thousands_group_style": "thousandsGroupStyle",
        "hide_controls": "hideControls",
        "start_value": "startValue",
        "with_keyboard_events": "withKeyboardEvents",
        "allow_mouse_wheel": "allowMouseWheel",
    }

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

    allow_decimal: Var[bool] = None
    """Allow decimal input (default: True)."""

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

    # Controls
    hide_controls: Var[bool] = None
    """Hide increment/decrement buttons."""

    start_value: Var[int | float] = None
    """Value when empty input is focused (default: 0)."""

    with_keyboard_events: Var[bool] = None
    """Enable up/down keyboard events for incrementing/decrementing (default: True).

    When True, pressing up/down arrow keys while focused increments/decrements
    the value by the step amount. Essential for keyboard-based navigation."""

    allow_mouse_wheel: Var[bool] = None
    """Enable mouse wheel increments/decrements (default: False)."""

    def get_event_triggers(self) -> dict[str, Any]:
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


number_input = NumberInput.create
