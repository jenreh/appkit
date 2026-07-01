"""Resources schedule + agenda examples (Mantine 9.4, ``@mantine/schedule``).

Wraps the resource-oriented schedule views (rooms/people as rows) and the
agenda view. Install with::

    uv add @mantine/schedule
"""

from __future__ import annotations

import reflex as rx

import appkit_mantine as mn
from appkit_user.authentication.templates import navbar_layout

from app.components.navbar import app_navbar

_RESOURCES: list[dict] = [
    {"id": "tokyo", "label": "Room: Tokyo"},
    {"id": "paris", "label": "Room: Paris"},
    {"id": "cairo", "label": "Room: Cairo"},
]

_EVENTS: list[dict] = [
    {
        "id": "1",
        "title": "Team standup",
        "start": "2026-05-21 09:00:00",
        "end": "2026-05-21 09:30:00",
        "color": "blue",
        "resourceId": "tokyo",
    },
    {
        "id": "2",
        "title": "Client meeting",
        "start": "2026-05-21 11:00:00",
        "end": "2026-05-21 12:30:00",
        "color": "violet",
        "resourceId": "paris",
    },
    {
        "id": "3",
        "title": "Interview",
        "start": "2026-05-21 14:00:00",
        "end": "2026-05-21 15:00:00",
        "color": "teal",
        "resourceId": "cairo",
    },
    {
        "id": "4",
        "title": "Sprint planning",
        "start": "2026-05-22 10:00:00",
        "end": "2026-05-22 11:30:00",
        "color": "orange",
        "resourceId": "tokyo",
    },
]


class ResourcesScheduleExState(rx.State):
    """State for the resources schedule examples."""

    date: str = "2026-05-21"
    view: str = "day"
    last_event: str = ""

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


def _section(title: str, description: str, *children: rx.Component) -> rx.Component:
    return rx.fragment(
        mn.title(title, order=2, mt="xl"),
        mn.text(description, size="sm", c="dimmed", mb="sm"),
        *children,
    )


def _framed(*children: rx.Component, h: str = "480px") -> rx.Component:
    return mn.card(
        *children,
        with_border=True,
        shadow="sm",
        radius="md",
        p="0",
        h=h,
        overflow="hidden",
    )


@navbar_layout(
    route="/resources-schedule",
    title="Resources Schedule",
    navbar=app_navbar(),
    with_header=False,
)
def resources_schedule_examples() -> rx.Component:
    """Page demonstrating the resource views and agenda view (Mantine 9.4)."""
    return mn.container(
        mn.stack(
            mn.title("Resources Schedule", order=1),
            mn.text(
                "Resource-oriented scheduling from @mantine/schedule — resources "
                "(rooms, people, equipment) render as rows, time as columns.",
                size="md",
                c="dimmed",
            ),
            mn.badge(
                "Requires: uv add @mantine/schedule",
                color="orange",
                mb="xs",
            ),
            rx.link("← Back to Home", href="/", size="3"),
            _section(
                "ResourcesSchedule (unified)",
                "All-in-one wrapper with day / week / month switching. Bind date"
                " and view to state for full control.",
            ),
            _framed(
                mn.resources_schedule(
                    resources=_RESOURCES,
                    events=_EVENTS,
                    date=ResourcesScheduleExState.date,
                    view=ResourcesScheduleExState.view,
                    on_date_change=ResourcesScheduleExState.on_date_change,
                    on_view_change=ResourcesScheduleExState.on_view_change,
                    on_event_click=ResourcesScheduleExState.on_event_click,
                    day_view_props={"startTime": "08:00:00", "endTime": "18:00:00"},
                    h="100%",
                ),
                h="560px",
            ),
            rx.cond(
                ResourcesScheduleExState.last_event != "",
                mn.badge(
                    "Last event: ",
                    mn.text(
                        ResourcesScheduleExState.last_event,
                        display="inline",
                        fw="bold",
                    ),
                    color="blue",
                    size="lg",
                    mt="sm",
                ),
                rx.fragment(),
            ),
            _section(
                "ResourcesDayView",
                "Resources as rows, a single day of time-slots as columns.",
            ),
            _framed(
                mn.resources_day_view(
                    resources=_RESOURCES,
                    events=_EVENTS,
                    date="2026-05-21",
                    start_time="08:00:00",
                    end_time="18:00:00",
                    with_current_time_indicator=True,
                    h="100%",
                ),
            ),
            _section(
                "ResourcesWeekView",
                "Resources as rows, a full week of time-slots as columns.",
            ),
            _framed(
                mn.resources_week_view(
                    resources=_RESOURCES,
                    events=_EVENTS,
                    date="2026-05-21",
                    start_time="08:00:00",
                    end_time="18:00:00",
                    h="100%",
                ),
            ),
            _section(
                "ResourcesMonthView",
                "Resources as rows, days as columns; weekend columns toggleable.",
            ),
            _framed(
                mn.resources_month_view(
                    resources=_RESOURCES,
                    events=_EVENTS,
                    date="2026-05-21",
                    with_weekend_days=False,
                    h="100%",
                ),
            ),
            _section(
                "AgendaView",
                "Vertical list of events grouped by date across a range.",
            ),
            mn.card(
                mn.agenda_view(
                    events=_EVENTS,
                    range_start="2026-05-18",
                    range_end="2026-05-24",
                    on_event_click=ResourcesScheduleExState.on_event_click,
                ),
                with_border=True,
                shadow="sm",
                radius="md",
                p="md",
            ),
            w="100%",
            mb="6rem",
            gap="sm",
        ),
        size="lg",
        w="100%",
    )
