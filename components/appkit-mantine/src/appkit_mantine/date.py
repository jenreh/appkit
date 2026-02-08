from __future__ import annotations

from typing import Any

import reflex as rx
from reflex.vars.base import Var

from appkit_mantine.base import MANTINE_VERSION, MantineInputComponentBase

DAYJS_VERSION: str = "1.11.18"


def _date_input_on_change(value: Var) -> list[Var]:
    """Event handler for DateInput on_change.

    Converts null/undefined values to empty string for Reflex state compatibility.
    Mantine DateInput sends null when cleared, but Reflex state fields typed as 'str'
    expect an empty string.
    """
    return [rx.Var(f"({value} ?? '')", _var_type=str)]


class DateInput(MantineInputComponentBase):
    """Mantine DateInput component for free form date input with calendar popup.

    Based on: https://mantine.dev/dates/date-input/

    Inherits common input props from MantineInputComponentBase.
    See `mantine_date_input()` function for detailed documentation and examples.
    """

    library = f"@mantine/dates@{MANTINE_VERSION}"
    lib_dependencies: list[str] = [f"dayjs@{DAYJS_VERSION}"]

    tag = "DateInput"
    alias = "MantineDateInput"

    # Date-specific props
    value_format: Var[str] = (
        None  # Day.js format for date display (e.g., "YYYY MMM DD")
    )
    date_parser: Var[Any] = None  # Custom date parser function
    clearable: Var[bool] = None  # Show clear button
    min_date: Var[str] = None  # Minimum allowed date
    max_date: Var[str] = None  # Maximum allowed date

    # Calendar/Popover props
    popover_props: Var[dict[str, Any]] = None  # Props passed to Popover component

    def get_event_triggers(self) -> dict[str, Any]:
        """Override event triggers to handle null values from Mantine.

        Converts null/undefined to empty string for Reflex state compatibility.
        """
        return {
            **super().get_event_triggers(),
            "on_change": _date_input_on_change,
        }

    def _get_custom_code(self) -> str | None:
        """Add CSS imports for Mantine DateInput.

        Note: Imports both core and dates CSS following Mantine Dates pattern.
        """
        return """import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';"""


date_input = DateInput.create
