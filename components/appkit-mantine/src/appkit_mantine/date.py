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

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        """Convert null/undefined to empty string/None for Reflex."""
        return {
            **super().get_event_triggers(),
            "on_change": _date_handler,
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

    with_native_level_select: Var[bool] = None
    """Replace the calendar header level button with native select elements
    (Mantine 9.5)."""

    presets: Var[list[dict[str, Any]]] = None
    """Presets shown next to the calendar: ``[{"value": ..., "label": ...}]``."""

    value_formatter: Var[Any] = None
    """JS function ``({ type, date, locale, format, labelSeparator }) => string``."""

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": _date_handler,
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

    with_native_level_select: Var[bool] = None
    """Replace the calendar header level button with native select elements
    (Mantine 9.5)."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": _date_handler,
        }


class MonthPickerInput(MantineDateInputBase):
    """MonthPickerInput component."""

    tag = "MonthPickerInput"

    presets: Var[list[Any]] = None
    """Predefined values to pick from (Mantine 9.1+)."""

    type: Var[DatePickerType] = None
    """Picker type: default, multiple, range."""

    value: Var[list[str] | str | Any] = None
    """Selected value."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            **super().get_event_triggers(),
            "on_change": _date_handler,
        }


class YearPickerInput(MantineDateInputBase):
    """YearPickerInput component."""

    tag = "YearPickerInput"

    presets: Var[list[Any]] = None
    """Predefined values to pick from (Mantine 9.1+)."""

    type: Var[DatePickerType] = None
    """Picker type: default, multiple, range."""

    value: Var[list[str] | str | Any] = None
    """Selected value."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
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

    with_native_level_select: Var[bool] = None
    """Replace the calendar header level button with native select elements
    (Mantine 9.5)."""

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        return {
            "on_change": _date_handler,
        }


class MonthPicker(MantineDateComponentBase):
    """MonthPicker component."""

    tag = "MonthPicker"

    presets: Var[list[Any]] = None
    """Predefined values to pick from (Mantine 9.1+)."""

    type: Var[DatePickerType] = None
    """Picker type."""

    value: Var[list[str] | str | Any] = None
    """Selected value."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    on_date_change: EventHandler[lambda date: [date]] = None
    """Called when date displayed changes."""

    with_native_level_select: Var[bool] = None
    """Replace the calendar header level button with native select elements
    (Mantine 9.5)."""


class YearPicker(MantineDateComponentBase):
    """YearPicker component."""

    tag = "YearPicker"

    presets: Var[list[Any]] = None
    """Predefined values to pick from (Mantine 9.1+)."""

    type: Var[DatePickerType] = None
    """Picker type."""

    value: Var[list[str] | str | Any] = None
    """Selected value."""

    on_change: EventHandler[lambda value: [value]] = None
    """Called when value changes."""

    with_native_level_select: Var[bool] = None
    """Replace the calendar header level button with native select elements
    (Mantine 9.5)."""


class TimePicker(MantineDateInputBase):
    """TimePicker component.

    Note: In some Mantine versions this behaves like TimeInput with specific
    picker controls.
    """

    tag = "TimePicker"

    type: Var[Literal["duration"]] = None
    """Type of time picker, 'duration' mode enables durations exceeding 24h."""

    with_seconds: Var[bool] = None
    """Enable seconds."""

    presets: Var[list[str] | list[dict[str, Any]]] = None
    """Time presets: ``["09:00", ...]`` or groups
    ``[{"label": ..., "values": [...]}]``."""

    close_dropdown_on_preset_select: Var[bool] = None
    """Close the dropdown after a preset is selected (Mantine 9.4)."""


class TimeGrid(MantineComponentBase):
    """TimeGrid component."""

    library = DATE_LIBRARY
    lib_dependencies = DATE_LIB_DEPENDENCIES
    tag = "TimeGrid"

    data: Var[list[str]] = None
    """Array of time values."""

    value: Var[str | None] = None
    """Controlled selected time."""

    default_value: Var[str | None] = None
    """Uncontrolled initial time."""

    allow_deselect: Var[bool] = None
    """Allow deselecting the active time by clicking it again."""

    format: Var[Literal["12h", "24h"]] = None
    """Time format displayed in the grid."""

    with_seconds: Var[bool] = None
    """Display the seconds part."""

    am_pm_labels: Var[dict[str, str]] = None
    """Labels for am/pm values, e.g. ``{"am": "AM", "pm": "PM"}``."""

    simple_grid_props: Var[dict[str, Any]] = None
    """Props for the underlying SimpleGrid, e.g. ``{"cols": 3, "spacing": "xs"}``."""

    get_control_props: Var[Any] = None
    """JS function ``(time) => props`` for each control."""

    radius: Var[str | int] = None
    size: Var[str] = None

    min_time: Var[str] = None
    """Controls before this time are disabled."""

    max_time: Var[str] = None
    """Controls after this time are disabled."""

    disable_time: Var[list[str] | Any] = None
    """Times to disable, or a JS predicate ``(time) => boolean``."""

    disabled: Var[bool] = None

    on_change: EventHandler[_date_handler] = None
    """Called with the selected time string (``""`` when deselected)."""

    def _get_custom_code(self) -> str:
        return "import '@mantine/dates/styles.css';"


class TimeValue(MantineComponentBase):
    """TimeValue component."""

    library = DATE_LIBRARY
    lib_dependencies = DATE_LIB_DEPENDENCIES
    tag = "TimeValue"

    def _get_custom_code(self) -> str:
        return "import '@mantine/dates/styles.css';"


class InlineDateTimePicker(MantineDateComponentBase):
    """Mantine InlineDateTimePicker — inline calendar + time picker combined.

    https://mantine.dev/dates/inline-date-time-picker/
    """

    tag = "InlineDateTimePicker"

    type: Var[Literal["default", "multiple", "range"]] = None
    value: Var[Any] = None
    default_value: Var[Any] = None
    size: Var[str] = None
    full_width: Var[bool] = None
    number_of_columns: Var[int] = None
    max_date: Var[str] = None
    min_date: Var[str] = None
    allow_deselect: Var[bool] = None
    allow_single_date_in_range: Var[bool] = None
    hide_outside_dates: Var[bool] = None
    hide_weekdays: Var[bool] = None
    highlight_today: Var[bool] = None
    with_cell_spacing: Var[bool] = None
    with_week_numbers: Var[bool] = None
    with_seconds: Var[bool] = None
    first_day_of_week: Var[int] = None
    default_level: Var[Literal["month", "year", "decade"]] = None
    level: Var[Literal["month", "year", "decade"]] = None
    max_level: Var[Literal["month", "year", "decade"]] = None

    on_change: EventHandler[lambda value: [value]] = None
    on_date_change: EventHandler[lambda date: [date]] = None
    on_level_change: EventHandler[lambda level: [level]] = None
    on_submit: EventHandler[rx.event.no_args_event_spec] = None


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
inline_date_time_picker = InlineDateTimePicker.create
