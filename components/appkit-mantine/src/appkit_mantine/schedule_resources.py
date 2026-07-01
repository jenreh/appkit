"""Mantine Schedule resource views and agenda view.

Wraps the ``@mantine/schedule`` resource-oriented views and the agenda view
added in Mantine 9.4:

* ``ResourcesDayView`` / ``ResourcesWeekView`` / ``ResourcesMonthView`` — display
  resources (rooms, people, equipment) as rows and time as columns.
* ``ResourcesSchedule`` — unified wrapper combining the three resource views.
* ``AgendaView`` — vertical list of events grouped by date.

Kept in a dedicated module so ``schedule.py`` stays under the 1000-line limit.
Reuses :class:`~appkit_mantine.schedule.MantineScheduleBase` for the shared
props, style imports and ``on_event_*`` triggers.

References:
    https://mantine.dev/x/schedule/
"""

from __future__ import annotations

from typing import Any

from reflex.event import EventHandler
from reflex.vars.base import Var

from appkit_mantine.schedule import MantineScheduleBase

# NOTE: Reflex auto-converts snake_case Var names to camelCase in the emitted
# JSX (e.g. ``render_event_body`` -> ``renderEventBody``), so these views need
# no explicit ``_rename_props`` — every prop below maps cleanly.


class _ResourcesViewBase(MantineScheduleBase):
    """Shared props for all resource views (resources as rows)."""

    resources: Var[list] = None
    """List of resource objects (``{id, label}``) rendered as rows (required)."""

    groups: Var[list] = None
    """Optional resource groups rendered as labelled headers."""

    group_label_width: Var[str | int] = None
    """Width of the group label column."""

    render_resource_label: Var[Any] = None
    """Render-prop for custom resource labels."""

    render_group_label: Var[Any] = None
    """Render-prop for custom group labels."""

    date: Var[str] = None
    """Controlled current date (ISO string)."""

    on_date_change: EventHandler[lambda date: [date]] = None
    """Called when the user navigates to a different date."""

    on_time_slot_click: EventHandler[lambda data: [data]] = None
    """Called when an empty time slot is clicked."""

    on_slot_drag_end: EventHandler[lambda data: [data]] = None
    """Called after a drag-to-select range gesture completes."""

    on_external_event_drop: EventHandler[lambda data: [data]] = None
    """Called when an event dragged from outside is dropped."""


class _ResourcesTimeViewBase(_ResourcesViewBase):
    """Shared time-grid props for the day and week resource views."""

    start_time: Var[str] = None
    """Earliest visible time slot, e.g. ``"08:00:00"``."""

    end_time: Var[str] = None
    """Latest visible time slot, e.g. ``"18:00:00"``."""

    interval_minutes: Var[int] = None
    """Granularity of time slots in minutes."""

    start_scroll_time: Var[str] = None
    """Initial scroll position time string."""

    slot_width: Var[str | int] = None
    """Width of each time-slot column."""

    row_height: Var[str | int] = None
    """Height of each resource row."""

    with_current_time_indicator: Var[bool] = None
    """Show a line at the current time."""

    with_current_time_bubble: Var[bool] = None
    """Show a bubble on the current-time indicator."""

    highlight_business_hours: Var[bool] = None
    """Highlight business-hours slots."""

    business_hours: Var[list | Any] = None
    """Business-hours range, e.g. ``["09:00:00", "17:00:00"]``."""

    max_events_per_time_slot: Var[int] = None
    """Max visible events per slot before ``+N more`` is shown."""

    with_drag_slot_select: Var[bool] = None
    """Allow creating events by dragging across empty slots."""

    slot_label_format: Var[Any] = None
    """Format string or function for time-slot labels."""


class ResourcesDayView(_ResourcesTimeViewBase):
    """Mantine ResourcesDayView — resources as rows, day time-slots as columns.

    https://mantine.dev/x/schedule/#resources-day-view
    """

    tag = "ResourcesDayView"


class ResourcesWeekView(_ResourcesTimeViewBase):
    """Mantine ResourcesWeekView — resources with a full week of time-slots.

    https://mantine.dev/x/schedule/#resources-week-view
    """

    tag = "ResourcesWeekView"


class ResourcesMonthView(_ResourcesViewBase):
    """Mantine ResourcesMonthView — resources as rows, days as columns.

    https://mantine.dev/x/schedule/#resources-month-view
    """

    tag = "ResourcesMonthView"

    day_width: Var[str | int] = None
    """Width of each day column."""

    start_scroll_date: Var[str] = None
    """Date scrolled to on initial load."""

    with_header: Var[bool] = None
    """Show the navigation header."""

    with_weekend_days: Var[bool] = None
    """Show/hide weekend day columns."""

    max_events_per_time_slot: Var[int] = None
    """Max events per cell before ``+N more`` is shown."""

    scroll_area_props: Var[dict] = None
    """Props forwarded to the inner Mantine ScrollArea."""

    on_day_click: EventHandler[lambda data: [data]] = None
    """Called when a day cell is clicked."""


class ResourcesSchedule(_ResourcesTimeViewBase):
    """Mantine ResourcesSchedule — unified resource scheduler with view switching.

    https://mantine.dev/x/schedule/#resources-schedule
    """

    tag = "ResourcesSchedule"

    default_date: Var[str] = None
    """Uncontrolled initial date."""

    view: Var[str] = None
    """Controlled view level: ``"day"`` | ``"week"`` | ``"month"``."""

    default_view: Var[str] = None
    """Uncontrolled initial view level."""

    on_view_change: EventHandler[lambda view: [view]] = None
    """Called when the view level changes."""

    day_view_props: Var[dict] = None
    week_view_props: Var[dict] = None
    month_view_props: Var[dict] = None

    on_day_click: EventHandler[lambda data: [data]] = None
    """Called when a month-view day cell is clicked."""


class AgendaView(MantineScheduleBase):
    """Mantine AgendaView — vertical list of events grouped by date.

    https://mantine.dev/x/schedule/#agenda-view
    """

    tag = "AgendaView"

    range_start: Var[str] = None
    """Start date of the agenda range (``YYYY-MM-DD``)."""

    range_end: Var[str] = None
    """End date of the agenda range (``YYYY-MM-DD``)."""

    header_format: Var[Any] = None
    """Format string or callback for the range header label."""

    date_header_format: Var[Any] = None
    """Format string or callback for per-date group headers."""


# ---------------------------------------------------------------------------
# Public factories
# ---------------------------------------------------------------------------

resources_day_view = ResourcesDayView.create
resources_week_view = ResourcesWeekView.create
resources_month_view = ResourcesMonthView.create
resources_schedule = ResourcesSchedule.create
agenda_view = AgendaView.create
