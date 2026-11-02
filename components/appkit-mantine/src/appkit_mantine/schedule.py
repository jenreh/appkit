"""Mantine Schedule extension components.

Wraps the ``@mantine/schedule`` package which provides calendar-style scheduling
views (day, week, month, year, mobile-month) plus a unified ``Schedule``
component that can render any of those views together.

References:
    https://mantine.dev/x/schedule/
"""

from __future__ import annotations

from typing import Any, Literal

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

    prevent_event_overlap: Var[bool | Any] = None
    """Reject drops/resizes that overlap other events; accepts a predicate
    deciding per pair of events (Mantine 9.7)."""

    can_drop_event: Var[Any] = None
    """Predicate returning ``False`` to reject a drop (Mantine 9.7)."""

    can_resize_event_to: Var[Any] = None
    """Predicate returning ``False`` to reject a resize (Mantine 9.7)."""

    can_drop_external_event: Var[Any] = None
    """Same check for items dragged in from outside the schedule (9.7)."""

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
            "on_event_placement_rejected": _one,
        }


# ---------------------------------------------------------------------------
# DayView
# ---------------------------------------------------------------------------


class DayView(MantineScheduleBase):
    """Mantine Schedule.DayView — single-day time-grid view.

    https://mantine.dev/x/schedule/#day-view
    """

    tag = "DayView"

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

    event_overlap_mode: Var[Literal["columns", "cascade"]] = None
    """How overlapping events share horizontal space (Mantine 9.7)."""

    event_overlap_raise_delay: Var[int] = None
    """Delay in ms before a hovered/focused event is raised (default 600)."""

    event_drag_interval: Var[int] = None
    """Snap step in minutes for dragging, independent of
    ``interval_minutes`` (Mantine 9.6)."""

    event_resize_interval: Var[int] = None
    """Snap step in minutes for resizing (Mantine 9.6)."""

    with_interactive_background_events: Var[bool] = None
    """Make ``display: "background"`` events clickable (Mantine 9.6)."""


# ---------------------------------------------------------------------------
# WeekView
# ---------------------------------------------------------------------------


class WeekView(MantineScheduleBase):
    """Mantine Schedule.WeekView — seven-column day-by-day time-grid.

    https://mantine.dev/x/schedule/#week-view
    """

    tag = "WeekView"

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

    event_overlap_mode: Var[Literal["columns", "cascade"]] = None
    event_overlap_raise_delay: Var[int] = None
    event_drag_interval: Var[int] = None
    event_resize_interval: Var[int] = None
    with_interactive_background_events: Var[bool] = None

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
    with_interactive_background_events: Var[bool] = None
    """Make ``display: "background"`` events clickable (Mantine 9.6)."""

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


class YearView(MantineScheduleBase):
    """Mantine Schedule.YearView — twelve-month overview.

    https://mantine.dev/x/schedule/#year-view
    """

    tag = "YearView"

    date: Var[str] = None
    on_date_change: EventHandler[lambda date: [date]] = None
    on_view_change: EventHandler[lambda view: [view]] = None
    on_day_click: EventHandler[lambda date: [date]] = None
    on_month_click: EventHandler[lambda date: [date]] = None
    """Called when a month tile is clicked."""

    first_day_of_week: Var[int] = None
    with_week_numbers: Var[bool] = None
    with_week_days: Var[bool] = None
    with_weekend_days: Var[bool] = None
    """Show/hide weekend day columns (Mantine 9.5).

    Weekend days are controlled by ``weekend_days`` (default ``[0, 6]``).
    """

    render_day: Var[Any] = None
    """Render-prop for custom day cell content (Mantine 9.5).

    Receives the day date (``YYYY-MM-DD``) and the events of that day.
    """

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


class MobileMonthView(MantineScheduleBase):
    """Mantine Schedule.MobileMonthView — compact month + events list for mobile.

    https://mantine.dev/x/schedule/#mobile-month-view
    """

    tag = "MobileMonthView"

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


class Schedule(MantineScheduleBase):
    """Mantine Schedule — unified scheduling calendar.

    Renders the appropriate view (day / week / month / year /
    mobile-month) based on the ``view`` prop and includes a
    navigation toolbar.

    https://mantine.dev/x/schedule/
    """

    tag = "Schedule"

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

    with_interactive_background_events: Var[bool] = None
    """Make ``display: "background"`` events clickable (Mantine 9.6)."""

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
