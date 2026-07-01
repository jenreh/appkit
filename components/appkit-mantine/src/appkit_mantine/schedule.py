"""Mantine Schedule extension components.

Wraps the ``@mantine/schedule`` package which provides calendar-style scheduling
views (day, week, month, year, mobile-month) plus a unified ``Schedule``
component that can render any of those views together.

References:
    https://mantine.dev/x/schedule/
"""

from __future__ import annotations

from typing import Any

import reflex as rx
from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.base import MANTINE_VERSION, MantineLayoutComponentBase

SCHEDULE_LIBRARY = f"@mantine/schedule@{MANTINE_VERSION}"


class MantineScheduleBase(MantineLayoutComponentBase):
    """Base class for all ``@mantine/schedule`` components.

    Declares all props shared by every schedule view so Reflex's field scanner
    registers them as component props (not style values).  Plain-Python mixins
    are NOT scanned by Reflex — all shared props must live here.
    """

    library = SCHEDULE_LIBRARY

    # ------------------------------------------------------------------
    # Shared schedule props (formerly in _ScheduleCommonMixin).
    # Must be declared here so Reflex treats them as component props.
    # ------------------------------------------------------------------

    events: Var[list] = None
    """List of schedule event objects to display."""

    locale: Var[str] = None
    """Locale string, e.g. ``"en"`` or ``"de"``."""

    radius: Var[str | int] = None
    """Border-radius of event cards (Mantine size or px value)."""

    labels: Var[dict] = None
    """Override default UI labels (localisation dict)."""

    mode: Var[str] = None
    """``"default"`` or ``"static"`` — controls navigation chrome."""

    render_event_body: Var[Any] = None
    """Render-prop for custom event body content."""

    render_event: Var[Any] = None
    """Render-prop to fully replace the default event element."""

    with_events_drag_and_drop: Var[bool] = None
    """Enable drag-and-drop repositioning of events."""

    can_drag_event: Var[Any] = None
    """Predicate function controlling whether an event can be dragged."""

    with_event_resize: Var[bool] = None
    """Enable resize handles on events."""

    can_resize_event: Var[Any] = None
    """Predicate function controlling whether an event can be resized."""

    recurrence_expansion_limit: Var[int] = None
    """Maximum number of recurring event instances to expand."""

    def _get_custom_code(self) -> str:
        return (
            "import '@mantine/core/styles.css';\n"
            "import '@mantine/dates/styles.css';\n"
            "import '@mantine/schedule/styles.css';"
        )

    @classmethod
    def get_event_triggers(cls) -> dict[str, Any]:
        # EventHandler fields are registered via get_event_triggers() because
        # Reflex does not auto-generate event triggers for EventHandler fields
        # declared on an rx.Component subclass the same way.
        def _one(v: Var) -> list[Var]:
            return [v]

        return {
            **super().get_event_triggers(),
            "on_event_click": _one,
            "on_event_drop": _one,
            "on_event_resize": _one,
        }


# ---------------------------------------------------------------------------
# _rename_props mapping for common schedule props.
# ---------------------------------------------------------------------------

_SCHEDULE_COMMON_RENAME: dict[str, str] = {
    "render_event_body": "renderEventBody",
    "render_event": "renderEvent",
    "with_events_drag_and_drop": "withEventsDragAndDrop",
    "on_event_drop": "onEventDrop",
    "can_drag_event": "canDragEvent",
    "with_event_resize": "withEventResize",
    "on_event_resize": "onEventResize",
    "can_resize_event": "canResizeEvent",
    "on_event_click": "onEventClick",
    "recurrence_expansion_limit": "recurrenceExpansionLimit",
}


# ---------------------------------------------------------------------------
# Shared rename-props for view-specific props that appear in multiple views.
# ---------------------------------------------------------------------------

_VIEW_SLOT_RENAME: dict[str, str] = {
    "with_drag_slot_select": "withDragSlotSelect",
    "on_slot_drag_end": "onSlotDragEnd",
    "on_time_slot_click": "onTimeSlotClick",
    "on_all_day_slot_click": "onAllDaySlotClick",
    "on_day_click": "onDayClick",
    "on_external_event_drop": "onExternalEventDrop",
    "scroll_area_props": "scrollAreaProps",
    "get_time_slot_props": "getTimeSlotProps",
}

_VIEW_TIME_RENAME: dict[str, str] = {
    "start_time": "startTime",
    "end_time": "endTime",
    "interval_minutes": "intervalMinutes",
    "start_scroll_time": "startScrollTime",
    "slot_height": "slotHeight",
    "all_day_slot_height": "allDaySlotHeight",
    "with_header": "withHeader",
    "header_format": "headerFormat",
    "slot_label_format": "slotLabelFormat",
    "highlight_business_hours": "highlightBusinessHours",
    "business_hours": "businessHours",
    "with_current_time_indicator": "withCurrentTimeIndicator",
    "with_current_time_bubble": "withCurrentTimeBubble",
    "with_all_day_slot": "withAllDaySlot",
    "with_sub_hour_grid_lines": "withSubHourGridLines",
    "with_agenda": "withAgenda",
    "get_current_time": "getCurrentTime",
    "on_date_change": "onDateChange",
    "on_view_change": "onViewChange",
}

_VIEW_WEEK_RENAME: dict[str, str] = {
    "first_day_of_week": "firstDayOfWeek",
    "weekend_days": "weekendDays",
    "weekday_format": "weekdayFormat",
    "highlight_today": "highlightToday",
    "with_week_number": "withWeekNumber",
    "force_current_time_indicator": "forceCurrentTimeIndicator",
    "with_all_day_slots": "withAllDaySlots",
    "week_label_format": "weekLabelFormat",
    "render_week_label": "renderWeekLabel",
}

_VIEW_MONTH_RENAME: dict[str, str] = {
    "first_day_of_week": "firstDayOfWeek",
    "with_week_numbers": "withWeekNumbers",
    "with_week_days": "withWeekDays",
    "with_weekend_days": "withWeekendDays",
    "with_agenda": "withAgenda",
    "consistent_weeks": "consistentWeeks",
    "highlight_today": "highlightToday",
    "with_outside_days": "withOutsideDays",
    "max_events_per_day": "maxEventsPerDay",
    "weekday_format": "weekdayFormat",
    "weekend_days": "weekendDays",
    "with_header": "withHeader",
    "with_drag_slot_select": "withDragSlotSelect",
    "on_slot_drag_end": "onSlotDragEnd",
    "on_external_event_drop": "onExternalEventDrop",
    "get_day_props": "getDayProps",
    "get_week_number_props": "getWeekNumberProps",
    "on_week_number_click": "onWeekNumberClick",
    "scroll_area_props": "scrollAreaProps",
    "on_day_click": "onDayClick",
    "on_date_change": "onDateChange",
    "on_view_change": "onViewChange",
}


# ---------------------------------------------------------------------------
# DayView
# ---------------------------------------------------------------------------


class DayView(MantineScheduleBase):
    """Mantine Schedule.DayView — single-day time-grid view.

    https://mantine.dev/x/schedule/#day-view
    """

    tag = "DayView"

    _rename_props = {
        **_SCHEDULE_COMMON_RENAME,
        **_VIEW_SLOT_RENAME,
        **_VIEW_TIME_RENAME,
    }

    date: Var[str] = None
    """Controlled current date (ISO string)."""

    on_date_change: EventHandler[lambda date: [date]] = None
    """Called when the user navigates to a different date."""

    on_view_change: EventHandler[lambda view: [view]] = None
    """Called when the user switches views."""

    start_time: Var[str] = None
    """Earliest visible time slot, e.g. ``"07:00"``."""

    end_time: Var[str] = None
    """Latest visible time slot, e.g. ``"22:00"``."""

    interval_minutes: Var[int] = None
    """Granularity of time slots in minutes (default 60)."""

    start_scroll_time: Var[str] = None
    """Initial scroll position time string."""

    slot_height: Var[str | int] = None
    """Height of each time slot row."""

    all_day_slot_height: Var[str | int] = None
    """Height of the all-day events row."""

    with_header: Var[bool] = None
    """Show the date header above the grid."""

    header_format: Var[Any] = None
    """Date-fns format string or render function for the header."""

    slot_label_format: Var[Any] = None
    """Format string or function for time-slot labels."""

    highlight_business_hours: Var[bool] = None
    """Highlight business-hours slots with a different background."""

    business_hours: Var[list | Any] = None
    """Business-hours definition (object or list of objects)."""

    with_current_time_indicator: Var[bool] = None
    """Show a line at the current time."""

    with_current_time_bubble: Var[bool] = None
    """Show a bubble at the current-time indicator."""

    with_all_day_slot: Var[bool] = None
    """Show the all-day slot row."""

    with_sub_hour_grid_lines: Var[bool] = None
    """Show grid lines for sub-hour intervals (Mantine 9.4)."""

    with_agenda: Var[bool] = None
    """Show the agenda view toggle button (Mantine 9.4)."""

    get_current_time: Var[Any] = None
    """Function returning the current time for a timezone-aware indicator
    (Mantine 9.3)."""

    with_drag_slot_select: Var[bool] = None
    """Allow creating events by dragging over empty slots."""

    on_slot_drag_end: EventHandler[lambda start, end: [start, end]] = None
    """Called after the user finishes dragging to select a time range."""

    on_time_slot_click: EventHandler[lambda data: [data]] = None
    """Called when an empty time slot is clicked."""

    on_all_day_slot_click: EventHandler[lambda date: [date]] = None
    """Called when the all-day slot header is clicked."""

    scroll_area_props: Var[dict] = None
    """Props forwarded to the inner Mantine ScrollArea."""

    get_time_slot_props: Var[Any] = None
    """Function returning extra props for individual time-slot elements."""


# ---------------------------------------------------------------------------
# WeekView
# ---------------------------------------------------------------------------


class WeekView(MantineScheduleBase):
    """Mantine Schedule.WeekView — seven-column day-by-day time-grid.

    https://mantine.dev/x/schedule/#week-view
    """

    tag = "WeekView"

    _rename_props = {
        **_SCHEDULE_COMMON_RENAME,
        **_VIEW_SLOT_RENAME,
        **_VIEW_TIME_RENAME,
        **_VIEW_WEEK_RENAME,
    }

    date: Var[str] = None
    """Controlled current week (ISO string for any day in the week)."""

    on_date_change: EventHandler[lambda date: [date]] = None
    on_view_change: EventHandler[lambda view: [view]] = None

    # -- Time-grid props (same as DayView) ----------------------------------
    start_time: Var[str] = None
    end_time: Var[str] = None
    interval_minutes: Var[int] = None
    start_scroll_time: Var[str] = None
    slot_height: Var[str | int] = None
    all_day_slot_height: Var[str | int] = None
    with_header: Var[bool] = None
    header_format: Var[Any] = None
    slot_label_format: Var[Any] = None
    highlight_business_hours: Var[bool] = None
    business_hours: Var[list | Any] = None
    with_current_time_indicator: Var[bool] = None
    with_current_time_bubble: Var[bool] = None
    with_all_day_slot: Var[bool] = None
    with_sub_hour_grid_lines: Var[bool] = None
    with_agenda: Var[bool] = None
    get_current_time: Var[Any] = None
    with_drag_slot_select: Var[bool] = None
    on_slot_drag_end: EventHandler[lambda start, end: [start, end]] = None
    on_time_slot_click: EventHandler[lambda data: [data]] = None
    on_all_day_slot_click: EventHandler[lambda date: [date]] = None
    scroll_area_props: Var[dict] = None
    get_time_slot_props: Var[Any] = None

    # -- Week-specific props ------------------------------------------------
    first_day_of_week: Var[int] = None
    """0 = Sunday … 6 = Saturday (default 1 = Monday)."""

    weekend_days: Var[list] = None
    """List of day numbers treated as weekend (e.g. ``[0, 6]``)."""

    weekday_format: Var[Any] = None
    """Date-fns format string or render function for weekday column headers."""

    highlight_today: Var[bool] = None
    """Highlight the column for today's date."""

    with_week_number: Var[bool] = None
    """Show an ISO week-number label."""

    force_current_time_indicator: Var[bool] = None
    """Always show the current-time indicator even when out of view."""

    with_all_day_slots: Var[bool] = None
    """Show per-column all-day slot rows."""

    week_label_format: Var[Any] = None
    """Format or render function for the week label."""

    render_week_label: Var[Any] = None
    """Render-prop for a fully custom week label."""


# ---------------------------------------------------------------------------
# MonthView
# ---------------------------------------------------------------------------


class MonthView(MantineScheduleBase):
    """Mantine Schedule.MonthView — full-month calendar grid.

    https://mantine.dev/x/schedule/#month-view
    """

    tag = "MonthView"

    _rename_props = {
        **_SCHEDULE_COMMON_RENAME,
        **_VIEW_MONTH_RENAME,
    }

    date: Var[str] = None
    """Controlled current month (ISO string)."""

    on_date_change: EventHandler[lambda date: [date]] = None
    on_view_change: EventHandler[lambda view: [view]] = None
    on_day_click: EventHandler[lambda date: [date]] = None
    """Called when a day cell is clicked."""

    on_external_event_drop: EventHandler[lambda data: [data]] = None
    """Called when an event dragged from outside the calendar is dropped."""

    first_day_of_week: Var[int] = None
    with_week_numbers: Var[bool] = None
    """Show ISO week-number labels on the left edge."""

    with_week_days: Var[bool] = None
    """Show weekday column headers."""

    consistent_weeks: Var[bool] = None
    """Always render 6 weeks so the grid height is consistent."""

    highlight_today: Var[bool] = None
    with_outside_days: Var[bool] = None
    """Show greyed-out days from the previous / next month."""

    max_events_per_day: Var[int] = None
    """Maximum visible events per day cell before "+N more" is shown."""

    weekday_format: Var[Any] = None
    weekend_days: Var[list] = None
    with_weekend_days: Var[bool] = None
    """Show/hide weekend day columns (Mantine 9.4)."""

    with_agenda: Var[bool] = None
    """Show the agenda view toggle button (Mantine 9.4)."""

    with_header: Var[bool] = None
    with_drag_slot_select: Var[bool] = None
    on_slot_drag_end: EventHandler[lambda start, end: [start, end]] = None
    scroll_area_props: Var[dict] = None
    get_day_props: Var[Any] = None
    """Function returning extra props for day cells."""

    get_week_number_props: Var[Any] = None
    """Function returning extra props for week-number cells."""

    on_week_number_click: EventHandler[lambda data: [data]] = None
    """Called when a week-number label is clicked."""


# ---------------------------------------------------------------------------
# YearView
# ---------------------------------------------------------------------------

_VIEW_YEAR_RENAME: dict[str, str] = {
    "first_day_of_week": "firstDayOfWeek",
    "with_week_numbers": "withWeekNumbers",
    "with_week_days": "withWeekDays",
    "with_outside_days": "withOutsideDays",
    "highlight_today": "highlightToday",
    "weekday_format": "weekdayFormat",
    "weekend_days": "weekendDays",
    "with_header": "withHeader",
    "month_label_format": "monthLabelFormat",
    "on_day_click": "onDayClick",
    "on_month_click": "onMonthClick",
    "on_week_number_click": "onWeekNumberClick",
    "get_day_props": "getDayProps",
    "get_week_number_props": "getWeekNumberProps",
    "on_date_change": "onDateChange",
    "on_view_change": "onViewChange",
}


class YearView(MantineScheduleBase):
    """Mantine Schedule.YearView — twelve-month overview.

    https://mantine.dev/x/schedule/#year-view
    """

    tag = "YearView"

    _rename_props = {
        **_SCHEDULE_COMMON_RENAME,
        **_VIEW_YEAR_RENAME,
    }

    date: Var[str] = None
    on_date_change: EventHandler[lambda date: [date]] = None
    on_view_change: EventHandler[lambda view: [view]] = None
    on_day_click: EventHandler[lambda date: [date]] = None
    on_month_click: EventHandler[lambda date: [date]] = None
    """Called when a month tile is clicked."""

    first_day_of_week: Var[int] = None
    with_week_numbers: Var[bool] = None
    with_week_days: Var[bool] = None
    with_outside_days: Var[bool] = None
    highlight_today: Var[bool] = None
    weekday_format: Var[Any] = None
    weekend_days: Var[list] = None
    with_header: Var[bool] = None
    month_label_format: Var[Any] = None
    """Format string or render function for each month label."""

    get_day_props: Var[Any] = None
    get_week_number_props: Var[Any] = None
    on_week_number_click: EventHandler[lambda data: [data]] = None


# ---------------------------------------------------------------------------
# MobileMonthView
# ---------------------------------------------------------------------------

_VIEW_MOBILE_RENAME: dict[str, str] = {
    "selected_date": "selectedDate",
    "on_selected_date_change": "onSelectedDateChange",
    "default_selected_date": "defaultSelectedDate",
    "events_header_format": "eventsHeaderFormat",
    "render_header": "renderHeader",
    "first_day_of_week": "firstDayOfWeek",
    "with_week_numbers": "withWeekNumbers",
    "with_outside_days": "withOutsideDays",
    "consistent_weeks": "consistentWeeks",
    "weekday_format": "weekdayFormat",
    "with_week_days": "withWeekDays",
    "highlight_today": "highlightToday",
    "weekend_days": "weekendDays",
    "on_day_click": "onDayClick",
    "on_week_number_click": "onWeekNumberClick",
    "on_year_click": "onYearClick",
    "get_day_props": "getDayProps",
    "get_week_number_props": "getWeekNumberProps",
    "recurrence_expansion_limit": "recurrenceExpansionLimit",
    "on_date_change": "onDateChange",
    "on_event_click": "onEventClick",
}


class MobileMonthView(MantineScheduleBase):
    """Mantine Schedule.MobileMonthView — compact month + events list for mobile.

    https://mantine.dev/x/schedule/#mobile-month-view
    """

    tag = "MobileMonthView"

    _rename_props = {
        **_SCHEDULE_COMMON_RENAME,
        **_VIEW_MOBILE_RENAME,
    }

    date: Var[str] = None
    on_date_change: EventHandler[lambda date: [date]] = None

    selected_date: Var[str] = None
    """Controlled selected date (ISO string) for the events list."""

    on_selected_date_change: EventHandler[lambda v: [v]] = None
    """Called when the user picks a day in the mini calendar."""

    default_selected_date: Var[str] = None
    """Uncontrolled default selected date."""

    events_header_format: Var[Any] = None
    """Format for the events-list section heading."""

    render_header: Var[Any] = None
    """Render-prop for a custom mini-calendar header."""

    first_day_of_week: Var[int] = None
    with_week_numbers: Var[bool] = None
    with_outside_days: Var[bool] = None
    consistent_weeks: Var[bool] = None
    weekday_format: Var[Any] = None
    with_week_days: Var[bool] = None
    highlight_today: Var[bool] = None
    weekend_days: Var[list] = None

    on_day_click: EventHandler[lambda date: [date]] = None
    on_week_number_click: EventHandler[lambda data: [data]] = None
    on_year_click: EventHandler[lambda year: [year]] = None
    """Called when the year label is clicked."""

    get_day_props: Var[Any] = None
    get_week_number_props: Var[Any] = None


# ---------------------------------------------------------------------------
# Schedule (unified all-in-one component)
# ---------------------------------------------------------------------------

_SCHEDULE_MAIN_RENAME: dict[str, str] = {
    **_SCHEDULE_COMMON_RENAME,
    "default_date": "defaultDate",
    "on_date_change": "onDateChange",
    "default_view": "defaultView",
    "on_view_change": "onViewChange",
    "with_agenda": "withAgenda",
    "day_view_props": "dayViewProps",
    "week_view_props": "weekViewProps",
    "month_view_props": "monthViewProps",
    "year_view_props": "yearViewProps",
    "mobile_month_view_props": "mobileMonthViewProps",
    "with_drag_slot_select": "withDragSlotSelect",
    "on_slot_drag_end": "onSlotDragEnd",
    "on_time_slot_click": "onTimeSlotClick",
    "on_all_day_slot_click": "onAllDaySlotClick",
    "on_day_click": "onDayClick",
    "on_external_event_drop": "onExternalEventDrop",
}


class Schedule(MantineScheduleBase):
    """Mantine Schedule — unified scheduling calendar.

    Renders the appropriate view (day / week / month / year /
    mobile-month) based on the ``view`` prop and includes a
    navigation toolbar.

    https://mantine.dev/x/schedule/
    """

    tag = "Schedule"

    _rename_props = _SCHEDULE_MAIN_RENAME

    date: Var[str] = None
    """Controlled current date (ISO string)."""

    default_date: Var[str] = None
    """Uncontrolled initial date."""

    on_date_change: EventHandler[lambda date: [date]] = None

    view: Var[str] = None
    """Controlled view level: ``"day"`` | ``"week"`` | ``"month"`` | ``"year"``."""

    default_view: Var[str] = None
    """Uncontrolled initial view level."""

    on_view_change: EventHandler[lambda view: [view]] = None

    with_agenda: Var[bool] = None
    """Show the agenda view toggle button (Mantine 9.4)."""

    layout: Var[str] = None
    """``"default"`` or ``"responsive"``.

    Switches to the mobile layout below a breakpoint.
    """

    day_view_props: Var[dict] = None
    week_view_props: Var[dict] = None
    month_view_props: Var[dict] = None
    year_view_props: Var[dict] = None
    mobile_month_view_props: Var[dict] = None

    with_drag_slot_select: Var[bool] = None
    on_slot_drag_end: EventHandler[lambda start, end: [start, end]] = None
    on_time_slot_click: EventHandler[lambda data: [data]] = None
    on_all_day_slot_click: EventHandler[lambda date: [date]] = None
    on_day_click: EventHandler[lambda date: [date]] = None
    on_external_event_drop: EventHandler[lambda data: [data]] = None


# ---------------------------------------------------------------------------
# Namespace + public factory
# ---------------------------------------------------------------------------


class ScheduleNamespace(rx.ComponentNamespace):
    """Namespace exposing ``schedule.*`` sub-components."""

    __call__ = staticmethod(Schedule.create)
    day_view = staticmethod(DayView.create)
    week_view = staticmethod(WeekView.create)
    month_view = staticmethod(MonthView.create)
    year_view = staticmethod(YearView.create)
    mobile_month_view = staticmethod(MobileMonthView.create)


schedule = ScheduleNamespace()
