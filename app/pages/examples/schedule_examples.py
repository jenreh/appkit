"""Schedule component examples — DayView, WeekView, MonthView, YearView.

Wraps ``@mantine/schedule``.  Install with::

    uv add @mantine/schedule
"""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar

# ---------------------------------------------------------------------------
# Sample events centred on 2026-05-21 (current week Mon 18 - Sun 24)
# ---------------------------------------------------------------------------

_EVENTS: list[dict] = [
    {
        "id": "1",
        "start": "2026-05-18T00:00:00",
        "end": "2026-05-19T23:59:59",
        "title": "Hackathon",
        "color": "red",
        "allDay": True,
    },
    {
        "id": "2",
        "start": "2026-05-19T09:00:00",
        "end": "2026-05-19T09:30:00",
        "title": "Daily standup",
        "color": "blue",
    },
    {
        "id": "3",
        "start": "2026-05-20T14:00:00",
        "end": "2026-05-20T15:30:00",
        "title": "Product review",
        "color": "teal",
    },
    {
        "id": "4",
        "start": "2026-05-21T09:00:00",
        "end": "2026-05-21T09:30:00",
        "title": "Daily standup",
        "color": "blue",
    },
    {
        "id": "5",
        "start": "2026-05-21T11:00:00",
        "end": "2026-05-21T12:30:00",
        "title": "Client meeting",
        "color": "violet",
    },
    {
        "id": "6",
        "start": "2026-05-21T15:00:00",
        "end": "2026-05-21T16:00:00",
        "title": "Sprint planning",
        "color": "orange",
    },
    {
        "id": "7",
        "start": "2026-05-22T09:00:00",
        "end": "2026-05-22T09:30:00",
        "title": "Daily standup",
        "color": "blue",
    },
    {
        "id": "8",
        "start": "2026-05-22T10:00:00",
        "end": "2026-05-22T11:00:00",
        "title": "1:1 with manager",
        "color": "green",
    },
    {
        "id": "9",
        "start": "2026-05-23T13:00:00",
        "end": "2026-05-23T14:00:00",
        "title": "Lunch & learn",
        "color": "pink",
    },
    {
        "id": "10",
        "start": "2026-05-12T10:00:00",
        "end": "2026-05-12T11:00:00",
        "title": "Monthly all-hands",
        "color": "indigo",
    },
    {
        "id": "11",
        "start": "2026-05-05T14:00:00",
        "end": "2026-05-05T15:00:00",
        "title": "Roadmap review",
        "color": "cyan",
    },
    {
        "id": "12",
        "start": "2026-05-28T09:00:00",
        "end": "2026-05-28T10:30:00",
        "title": "Quarterly planning",
        "color": "yellow",
    },
]

_INTERVAL_EVENTS: list[dict] = [
    {
        "id": "i1",
        "start": "2026-05-21T09:00:00",
        "end": "2026-05-21T09:30:00",
        "title": "Morning standup",
        "color": "blue",
    },
    {
        "id": "i2",
        "start": "2026-05-21T11:00:00",
        "end": "2026-05-21T12:00:00",
        "title": "Team meeting",
        "color": "green",
    },
    {
        "id": "i3",
        "start": "2026-05-21T13:00:00",
        "end": "2026-05-21T14:30:00",
        "title": "Out of office",
        "color": "gray",
        "display": "background",
    },
]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class ScheduleExState(rx.State):
    """State for Schedule examples."""

    date: str = "2026-05-21"
    view: str = "week"
    last_event: str = ""
    last_day: str = ""
    rejected: str = ""
    interval_events: list[dict] = _INTERVAL_EVENTS

    @rx.event
    def move_interval_event(self, data: dict) -> None:
        self.interval_events = [
            {**event, "start": data["newStart"], "end": data["newEnd"]}
            if event["id"] == data.get("eventId")
            else event
            for event in self.interval_events
        ]

    @rx.event
    def on_date_change(self, date: str) -> None:
        self.date = date

    @rx.event
    def on_view_change(self, view: str) -> None:
        self.view = view

    @rx.event
    def on_event_click(self, event: dict) -> None:
        title = event.get("title", "") if isinstance(event, dict) else str(event)
        self.last_event = str(title)

    @rx.event
    def on_placement_rejected(self, data: dict) -> None:
        event = data.get("event", {}) if isinstance(data, dict) else {}
        self.rejected = f"Rejected: {event.get('title', '')}"

    @rx.event
    def on_day_click(self, date: str) -> None:
        self.last_day = str(date)


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------


def _section(title: str, description: str, *children: rx.Component) -> rx.Component:
    return rx.fragment(
        mn.title(title, order=2, mt="xl"),
        mn.text(description, size="sm", c="dimmed", mb="sm"),
        *children,
    )


def _framed(*children: rx.Component, h: str = "500px") -> rx.Component:
    """Wrap a schedule view in a bordered, overflow-clipped card."""
    return mn.card(
        *children,
        with_border=True,
        shadow="sm",
        radius="md",
        p="0",
        h=h,
        overflow="hidden",
    )


def _event_badges() -> rx.Component:
    return mn.group(
        rx.cond(
            ScheduleExState.last_event != "",
            mn.badge(
                "Last event: ",
                mn.text(
                    ScheduleExState.last_event,
                    display="inline",
                    fw="bold",
                ),
                color="blue",
                size="lg",
            ),
            rx.fragment(),
        ),
        rx.cond(
            ScheduleExState.last_day != "",
            mn.badge(
                "Last day click: ",
                mn.text(
                    ScheduleExState.last_day,
                    display="inline",
                    fw="bold",
                ),
                color="teal",
                size="lg",
            ),
            rx.fragment(),
        ),
        gap="sm",
        mt="sm",
    )


@navbar_layout(
    route="/examples/schedule",
    title="Schedule",
    navbar=app_navbar(),
    with_header=False,
)
def schedule_examples() -> rx.Component:
    """Page demonstrating the @mantine/schedule extension components."""
    return mn.container(
        mn.stack(
            mn.title("Schedule", order=1),
            mn.text(
                "Scheduling calendar from @mantine/schedule — day, week, "
                "month, year and mobile-month views.",
                size="md",
                c="dimmed",
            ),
            mn.badge(
                "Requires: uv add @mantine/schedule",
                color="orange",
                mb="xs",
            ),
            rx.link("← Back to Home", href="/", size="3"),
            # ------------------------------------------------------------------
            # Unified Schedule (controlled view + date)
            # ------------------------------------------------------------------
            _section(
                "Unified Schedule (mn.schedule)",
                "The all-in-one component renders a toolbar that lets users"
                " switch between day / week / month / year views. Bind"
                " view and date to state for full control.",
            ),
            _framed(
                mn.schedule(
                    events=_EVENTS,
                    date=ScheduleExState.date,
                    view=ScheduleExState.view,
                    on_date_change=ScheduleExState.on_date_change,
                    on_view_change=ScheduleExState.on_view_change,
                    on_event_click=ScheduleExState.on_event_click,
                    on_day_click=ScheduleExState.on_day_click,
                    h="100%",
                ),
                h="580px",
            ),
            _event_badges(),
            # ------------------------------------------------------------------
            # WeekView
            # ------------------------------------------------------------------
            _section(
                "WeekView (mn.schedule.week_view)",
                "7-column time-grid. Supports all-day slots, business-hour"
                " highlighting, and the current-time indicator.",
            ),
            _framed(
                mn.schedule.week_view(
                    events=_EVENTS,
                    date="2026-05-21",
                    highlight_today=True,
                    with_current_time_indicator=True,
                    with_all_day_slot=True,
                    highlight_business_hours=True,
                    h="100%",
                ),
            ),
            # ------------------------------------------------------------------
            # DayView
            # ------------------------------------------------------------------
            _section(
                "DayView (mn.schedule.day_view)",
                "Single-day time-grid. Scrolls to the configured"
                " start_scroll_time on mount.",
            ),
            _framed(
                mn.schedule.day_view(
                    events=_EVENTS,
                    date="2026-05-21",
                    start_time="07:00",
                    end_time="21:00",
                    with_current_time_indicator=True,
                    with_all_day_slot=True,
                    highlight_business_hours=True,
                    start_scroll_time="08:00",
                    h="100%",
                ),
                h="480px",
            ),
            # ------------------------------------------------------------------
            # MonthView
            # ------------------------------------------------------------------
            _section(
                "MonthView (mn.schedule.month_view)",
                "Classic calendar grid with week-number labels and"
                " configurable overflow (max_events_per_day).",
            ),
            _framed(
                mn.schedule.month_view(
                    events=_EVENTS,
                    date="2026-05-21",
                    highlight_today=True,
                    with_week_numbers=True,
                    consistent_weeks=True,
                    max_events_per_day=3,
                    h="100%",
                ),
            ),
            # ------------------------------------------------------------------
            # YearView
            # ------------------------------------------------------------------
            _section(
                "YearView (mn.schedule.year_view)",
                "Twelve-month overview that highlights event days. Mantine 9.5"
                " adds render_day for fully custom day cells and"
                " with_weekend_days=False to hide weekend days.",
            ),
            mn.card(
                mn.schedule.year_view(
                    events=_EVENTS,
                    date="2026-05-21",
                    highlight_today=True,
                    with_week_days=True,
                ),
                with_border=True,
                shadow="sm",
                radius="md",
                p="md",
            ),
            _section(
                "YearView without weekend days",
                "with_weekend_days=False hides Saturday and Sunday columns;"
                " which days count as weekend is controlled by weekend_days"
                " (default [0, 6]).",
            ),
            mn.card(
                mn.schedule.year_view(
                    events=_EVENTS,
                    date="2026-05-21",
                    highlight_today=True,
                    with_week_days=True,
                    with_weekend_days=False,
                ),
                with_border=True,
                shadow="sm",
                radius="md",
                p="md",
            ),
            # ------------------------------------------------------------------
            # MobileMonthView
            # ------------------------------------------------------------------
            _section(
                "MobileMonthView (mn.schedule.mobile_month_view)",
                "Compact month picker + scrollable events list — optimised"
                " for small screens.",
            ),
            _framed(
                mn.schedule.mobile_month_view(
                    events=_EVENTS,
                    date="2026-05-21",
                    default_selected_date="2026-05-21",
                    highlight_today=True,
                    consistent_weeks=True,
                    h="100%",
                ),
                h="600px",
            ),
            # ------------------------------------------------------------------
            # Overlap handling (Mantine 9.7)
            # ------------------------------------------------------------------
            _section(
                "Overlap mode & drop validation (Mantine 9.7)",
                "event_overlap_mode='cascade' stacks overlapping events;"
                " prevent_event_overlap rejects drags and resizes that would"
                " overlap another event.",
            ),
            mn.text(ScheduleExState.rejected, size="sm", c="red"),
            _framed(
                mn.schedule.week_view(
                    events=_EVENTS,
                    date="2026-05-21",
                    event_overlap_mode="cascade",
                    event_overlap_raise_delay=400,
                    with_events_drag_and_drop=True,
                    with_event_resize=True,
                    prevent_event_overlap=True,
                    on_event_placement_rejected=ScheduleExState.on_placement_rejected,
                    h="100%",
                ),
            ),
            # ------------------------------------------------------------------
            # Drag / resize intervals (Mantine 9.6)
            # ------------------------------------------------------------------
            _section(
                "Drag & resize intervals (Mantine 9.6)",
                "A 30-minute grid with 15-minute drag and resize snapping"
                " (event_drag_interval / event_resize_interval). The grey"
                " background block is clickable via"
                " with_interactive_background_events.",
            ),
            mn.text("Clicked: " + ScheduleExState.last_event, size="sm", c="dimmed"),
            _framed(
                mn.schedule.day_view(
                    events=ScheduleExState.interval_events,
                    date="2026-05-21",
                    start_time="08:00:00",
                    end_time="18:00:00",
                    interval_minutes=30,
                    event_drag_interval=15,
                    event_resize_interval=15,
                    with_sub_hour_grid_lines=False,
                    with_events_drag_and_drop=True,
                    with_event_resize=True,
                    with_interactive_background_events=True,
                    on_event_drop=ScheduleExState.move_interval_event,
                    on_event_resize=ScheduleExState.move_interval_event,
                    on_event_click=ScheduleExState.on_event_click,
                    h="100%",
                ),
            ),
            w="100%",
            mb="6rem",
            gap="sm",
        ),
        size="lg",
        w="100%",
    )
