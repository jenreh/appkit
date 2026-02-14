"""Mantine Date components for Reflex.

Wrappers for @mantine/dates components.
"""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import (
    MANTINE_VERSION,
    MantineComponentBase,
    MantineInputComponentBase,
)

# Constants
DATE_LIBRARY = f"@mantine/dates@{MANTINE_VERSION}"
DATE_LIB_DEPENDENCIES = ["dayjs@1.11.19"]

# Types
ConfigType = Literal["default", "month", "year"]
DatePickerType = Literal["default", "multiple", "range"]


def _date_handler(value: Var) -> list[Var]:
    """Handle date change events.

    Ensures that empty values are handled gracefully.
    """
    return [rx.Var(f"({value} ?? '')", _var_type=str)]


class MantineDateComponentBase(MantineComponentBase):
    """Base class for all Mantine Date components."""

    library = DATE_LIBRARY
    lib_dependencies = DATE_LIB_DEPENDENCIES

    def _get_custom_code(self) -> str:
        return "import '@mantine/dates/styles.css';"

    # Common props
    locale: Var[str] = None
    """Locale used for all labels formatting."""

    default_date: Var[str | Any] = None
    """Date displayed when value is empty."""

    date: Var[str | Any] = None
    """Controlled date displayed in calendar."""

    on_date_change: EventHandler[lambda date: [date]] = None
    """Called when date changes."""

    min_date: Var[str | Any] = None
    """Minimum possible date."""

    max_date: Var[str | Any] = None
    """Maximum possible date."""

    allow_deselect: Var[bool] = None
    """Determines whether value can be deselected when clicking on selected date."""


class MantineDateInputBase(MantineInputComponentBase):
    """Base class for date/time input components."""

    library = DATE_LIBRARY
    lib_dependencies = DATE_LIB_DEPENDENCIES

    def _get_custom_code(self) -> str:
        return "import '@mantine/dates/styles.css';"

    # Common props for inputs
    value_format: Var[str] = None
    """Format of the date displayed in input."""

    fix_on_blur: Var[bool] = None
    """Determines whether input value should be fixed on blur."""

    clearable: Var[bool] = None
    """Determines whether input value can be cleared."""

    # Popover props
    dropdown_type: Var[Literal["popover", "modal"]] = None
    """Where to show the calendar."""

    modal_props: Var[dict[str, Any]] = None
    """Props passed down to the modal."""

    popover_props: Var[dict[str, Any]] = None
    """Props passed down to the popover."""

    # Date props shared with pickers
    min_date: Var[str | Any] = None
    """Minimum possible date."""

    max_date: Var[str | Any] = None
    """Maximum possible date."""

    locale: Var[str] = None
    """Locale used for labels formatting."""

    _rename_props = {
        **MantineInputComponentBase._rename_props,  # noqa: SLF001
        "value_format": "valueFormat",
        "fix_on_blur": "fixOnBlur",
        "dropdown_type": "dropdownType",
        "modal_props": "modalProps",
        "popover_props": "popoverProps",
        "min_date": "minDate",
        "max_date": "maxDate",
        "default_date": "defaultDate",
        "allow_deselect": "allowDeselect",
    }


class DateInput(MantineDateInputBase):
    """DateInput component."""

    tag = "DateInput"
    alias = "MantineDateInput"

    date_parser: Var[Any] = None
    """Function to parse date from string."""

    value: Var[str | Any] = None
    """Current value."""

    default_value: Var[str | Any] = None
    """Default value."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    def get_event_triggers(self) -> dict[str, Any]:
        """Convert null/undefined to empty string/None for Reflex."""
        return {
            **super().get_event_triggers(),
            "on_change": _date_handler,
        }

    _rename_props = {
        **MantineDateInputBase._rename_props,  # noqa: SLF001
        "date_parser": "dateParser",
    }


class DatePickerInput(MantineDateInputBase):
    """DatePickerInput component."""

    tag = "DatePickerInput"

    type: Var[DatePickerType] = None
    """Picker type: default, multiple, range."""

    value: Var[list[str] | str | Any] = None
    """Selected value."""

    default_value: Var[list[str] | str | Any] = None
    """Default value."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    on_date_change: EventHandler[lambda date: [date]] = None
    """Called when date displayed in calendar changes."""

    # Calendar props
    number_of_columns: Var[int] = None
    """Number of columns to render."""

    hide_outside_dates: Var[bool] = None
    """Remove outside dates."""

    weekend_days: Var[list[int]] = None
    """Indices of weekend days."""

    first_day_of_week: Var[int] = None
    """First day of the week (0-6)."""

    def get_event_triggers(self) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": _date_handler,
        }

    _rename_props = {
        **MantineDateInputBase._rename_props,  # noqa: SLF001
        "number_of_columns": "numberOfColumns",
        "hide_outside_dates": "hideOutsideDates",
        "weekend_days": "weekendDays",
        "first_day_of_week": "firstDayOfWeek",
        "on_date_change": "onDateChange",
    }


class DateTimePicker(MantineDateInputBase):
    """DateTimePicker component."""

    tag = "DateTimePicker"

    value: Var[str | Any] = None
    """Selected value."""

    default_value: Var[str | Any] = None
    """Default value."""

    with_seconds: Var[bool] = None
    """Determines whether seconds input should be rendered."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    def get_event_triggers(self) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": _date_handler,
        }

    _rename_props = {
        **MantineDateInputBase._rename_props,  # noqa: SLF001
        "with_seconds": "withSeconds",
    }


class MonthPickerInput(MantineDateInputBase):
    """MonthPickerInput component."""

    tag = "MonthPickerInput"

    type: Var[DatePickerType] = None
    """Picker type: default, multiple, range."""

    value: Var[list[str] | str | Any] = None
    """Selected value."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    def get_event_triggers(self) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": _date_handler,
        }


class YearPickerInput(MantineDateInputBase):
    """YearPickerInput component."""

    tag = "YearPickerInput"

    type: Var[DatePickerType] = None
    """Picker type: default, multiple, range."""

    value: Var[list[str] | str | Any] = None
    """Selected value."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    def get_event_triggers(self) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": _date_handler,
        }


class TimeInput(MantineInputComponentBase):
    """TimeInput component."""

    tag = "TimeInput"
    library = DATE_LIBRARY
    lib_dependencies = DATE_LIB_DEPENDENCIES

    def _get_custom_code(self) -> str:
        return "import '@mantine/dates/styles.css';"

    with_seconds: Var[bool] = None
    """Determines whether seconds input should be rendered."""

    with_asterisk: Var[bool] = None
    """Add asterisk to label."""

    _rename_props = {
        **MantineInputComponentBase._rename_props,  # noqa: SLF001
        "with_seconds": "withSeconds",
        "with_asterisk": "withAsterisk",
    }


# --------------------------
# Inline Pickers
# --------------------------


class Calendar(MantineDateComponentBase):
    """Calendar component."""

    tag = "Calendar"

    static: Var[bool] = None
    """Determines whether calendar should be static."""

    date: Var[str | Any] = None
    """Current date."""

    on_date_change: EventHandler[lambda date: [date]] = None
    """Called when date changes."""

    render_day: Var[Any] = None
    """Render day function."""

    _rename_props = {
        "on_date_change": "onDateChange",
        "render_day": "renderDay",
        "min_date": "minDate",
        "max_date": "maxDate",
        "default_date": "defaultDate",
        "allow_deselect": "allowDeselect",
    }


class MiniCalendar(Calendar):
    """MiniCalendar component."""

    tag = "MiniCalendar"


class DatePicker(MantineDateComponentBase):
    """DatePicker component."""

    tag = "DatePicker"

    type: Var[DatePickerType] = None
    """Picker type: default, multiple, range."""

    value: Var[list[str] | str | Any] = None
    """Selected value."""

    default_value: Var[list[str] | str | Any] = None
    """Default value."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    number_of_columns: Var[int] = None
    """Number of columns to render."""

    hide_outside_dates: Var[bool] = None
    """Remove outside dates."""

    weekend_days: Var[list[int]] = None
    """Indices of weekend days."""

    def get_event_triggers(self) -> dict[str, Any]:
        return {
            "on_change": _date_handler,
        }

    _rename_props = {
        "number_of_columns": "numberOfColumns",
        "hide_outside_dates": "hideOutsideDates",
        "weekend_days": "weekendDays",
        "min_date": "minDate",
        "max_date": "maxDate",
        "default_date": "defaultDate",
        "allow_deselect": "allowDeselect",
        "default_value": "defaultValue",
    }


class MonthPicker(MantineDateComponentBase):
    """MonthPicker component."""

    tag = "MonthPicker"

    type: Var[DatePickerType] = None
    """Picker type."""

    value: Var[list[str] | str | Any] = None
    """Selected value."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    on_date_change: EventHandler[lambda date: [date]] = None
    """Called when date displayed changes."""

    _rename_props = {
        "on_date_change": "onDateChange",
        "min_date": "minDate",
        "max_date": "maxDate",
        "default_date": "defaultDate",
        "allow_deselect": "allowDeselect",
    }


class YearPicker(MantineDateComponentBase):
    """YearPicker component."""

    tag = "YearPicker"

    type: Var[DatePickerType] = None
    """Picker type."""

    value: Var[list[str] | str | Any] = None
    """Selected value."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    _rename_props = {
        "on_date_change": "onDateChange",
        "min_date": "minDate",
        "max_date": "maxDate",
        "default_date": "defaultDate",
        "allow_deselect": "allowDeselect",
    }


class TimePicker(MantineDateInputBase):
    """TimePicker component.

    Note: In some Mantine versions this behaves like TimeInput with specific
    picker controls.
    """

    tag = "TimePicker"

    with_seconds: Var[bool] = None
    """Enable seconds."""

    _rename_props = {
        **MantineDateInputBase._rename_props,  # noqa: SLF001
        "with_seconds": "withSeconds",
    }


class TimeGrid(MantineComponentBase):
    """TimeGrid component."""

    library = DATE_LIBRARY
    lib_dependencies = DATE_LIB_DEPENDENCIES
    tag = "TimeGrid"

    data: Var[list[str]] = None
    """Array of time values."""

    def _get_custom_code(self) -> str:
        return "import '@mantine/dates/styles.css';"


class TimeValue(MantineComponentBase):
    """TimeValue component."""

    library = DATE_LIBRARY
    lib_dependencies = DATE_LIB_DEPENDENCIES
    tag = "TimeValue"

    def _get_custom_code(self) -> str:
        return "import '@mantine/dates/styles.css';"


# Convenience functions
calendar = Calendar.create
date_input = DateInput.create
date_picker = DatePicker.create
date_picker_input = DatePickerInput.create
date_time_picker = DateTimePicker.create
mini_calendar = MiniCalendar.create
month_picker = MonthPicker.create
month_picker_input = MonthPickerInput.create
time_grid = TimeGrid.create
time_input = TimeInput.create
time_picker = TimePicker.create
time_value = TimeValue.create
year_picker = YearPicker.create
year_picker_input = YearPickerInput.create
