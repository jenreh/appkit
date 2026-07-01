# Schedule Reference

`@mantine/schedule` provides calendar-style scheduling views (day / week / month /
year / mobile-month) plus a unified `Schedule` component that renders any of them
with navigation chrome.

Access via the `mn.schedule` namespace:

| Factory | Component | Purpose |
| --- | --- | --- |
| `mn.schedule(...)` | Schedule | Unified view-switching calendar |
| `mn.schedule.day_view(...)` | DayView | Single-day time grid |
| `mn.schedule.week_view(...)` | WeekView | Multi-day time grid |
| `mn.schedule.month_view(...)` | MonthView | Month grid with day cells |
| `mn.schedule.year_view(...)` | YearView | 12 mini-month grids |
| `mn.schedule.mobile_month_view(...)` | MobileMonthView | Stacked agenda for mobile |

All views inherit from `MantineScheduleBase` which exposes a shared set of props.

## Shared props (every view)

```python
mn.schedule.day_view(
    events=State.events,  # list of {id, title, start, end, ...}
    locale="de",
    radius="md",
    labels={"today": "Heute"},  # localisation overrides
    mode="default",  # "default" | "static"
    render_event=lambda event: ...,  # full custom render
    render_event_body=lambda event: ...,  # custom body only
    with_events_drag_and_drop=True,
    can_drag_event=lambda event: event.draggable,
    with_event_resize=True,
    can_resize_event=lambda event: event.resizable,
    recurrence_expansion_limit=100,
    on_event_click=State.open_event,  # receives event
    on_event_drop=State.move_event,
    on_event_resize=State.resize_event,
)
```

`events` items shape (Mantine convention):

```python
{
    "id": "evt-1",
    "title": "Team standup",
    "start": "2025-01-27T09:00:00",
    "end": "2025-01-27T09:30:00",
    "color": "blue",
    # optional: "allDay": bool, "rrule": str, "data": dict, ...
}
```

## Unified Schedule

```python
mn.schedule(
    events=State.events,
    date=State.current_date,
    on_date_change=State.set_current_date,  # receives ISO date string
    view=State.current_view,  # "day" | "week" | "month" | "year"
    on_view_change=State.set_current_view,
    layout="responsive",  # "default" | "responsive"
    locale="en",
    day_view_props={"start_time": "08:00", "end_time": "20:00"},
    week_view_props={"first_day_of_week": 1, "weekend_days": [0, 6]},
    month_view_props={"max_events_per_day": 3},
    year_view_props={},
    mobile_month_view_props={},
    on_day_click=State.on_day_click,
    on_event_click=State.open_event,
)
```

Props specific to the unified `Schedule`:
- `date`, `default_date`, `on_date_change`
- `view`, `default_view`, `on_view_change`
- `layout` (`"default"` | `"responsive"`)
- `day_view_props`, `week_view_props`, `month_view_props`, `year_view_props`,
  `mobile_month_view_props` — per-view prop dicts.
- All shared event handlers (`on_event_click`, `on_event_drop`, etc.)
- Slot interaction: `with_drag_slot_select`, `on_slot_drag_end`,
  `on_time_slot_click`, `on_all_day_slot_click`, `on_day_click`,
  `on_external_event_drop`.

## DayView / WeekView (time-grid views)

Common props (in addition to shared props):

- `start_time` / `end_time` — visible window (`"HH:MM"`).
- `interval_minutes` — slot height interval.
- `start_scroll_time` — initial scroll position.
- `slot_height`, `all_day_slot_height` — pixel sizes.
- `with_header`, `header_format`, `slot_label_format`.
- `with_current_time_indicator`, `with_current_time_bubble`, `with_all_day_slot`.
- `highlight_business_hours`, `business_hours`.
- `with_drag_slot_select`, `on_slot_drag_end`, `on_time_slot_click`,
  `on_all_day_slot_click`, `on_day_click`, `on_external_event_drop`,
  `scroll_area_props`, `get_time_slot_props`.
- `on_date_change`, `on_view_change`.

`WeekView` additionally:
- `first_day_of_week` (0 Sun, 1 Mon).
- `weekend_days` (list of ints).
- `weekday_format`.
- `highlight_today`.
- `with_week_number`, `with_all_day_slots`.

## MonthView

- `first_day_of_week`, `weekend_days`, `weekday_format`.
- `with_week_numbers`, `with_week_days`, `with_header`.
- `consistent_weeks`, `highlight_today`, `with_outside_days`.
- `max_events_per_day`.
- `with_drag_slot_select`, `on_slot_drag_end`, `on_external_event_drop`,
  `get_day_props`, `get_week_number_props`, `on_week_number_click`,
  `scroll_area_props`, `on_day_click`, `on_date_change`, `on_view_change`.

## YearView

Renders 12 mini-months. Props: shared props plus
`first_day_of_week`, `weekend_days`, `highlight_today`, `with_outside_days`,
`with_week_numbers`, `on_day_click`, `on_month_click`.

## MobileMonthView

Stacked agenda layout for narrow viewports. Props: shared props plus
`first_day_of_week`, `with_outside_days`, `on_day_click`, `on_date_change`.

## Resource views (Mantine 9.4)

Resource-oriented views render resources (rooms, people, equipment) as **rows**
and time as **columns**. Each resource is `{id, label}`; events reference a
resource via `resourceId`.

```python
resources = [{"id": "tokyo", "label": "Room: Tokyo"},
             {"id": "paris", "label": "Room: Paris"}]
events = [{"id": "1", "title": "Standup", "start": "2026-05-21 09:00:00",
           "end": "2026-05-21 09:30:00", "resourceId": "tokyo", "color": "blue"}]

# Unified wrapper (day / week / month switching)
mn.resources_schedule(
    resources=resources, events=events,
    date=State.date, on_date_change=State.set_date,
    view=State.view, on_view_change=State.set_view,
    day_view_props={"startTime": "08:00:00", "endTime": "18:00:00"},
)

# Individual views
mn.resources_day_view(resources=resources, events=events, date="2026-05-21",
                      start_time="08:00:00", end_time="18:00:00")
mn.resources_week_view(resources=resources, events=events, date="2026-05-21")
mn.resources_month_view(resources=resources, events=events, date="2026-05-21",
                        with_weekend_days=False)
```

Shared props: `resources`, `events`, `date`, `on_date_change`, `groups`,
`group_label_width`, `render_resource_label`, `mode` (`"static"` = read-only),
`with_events_drag_and_drop`, `with_event_resize`, `on_event_click`,
`on_event_drop`, `on_time_slot_click`. Day/Week add `start_time`, `end_time`,
`interval_minutes`, `slot_width`, `row_height`, `with_current_time_indicator`.
Month adds `day_width`, `with_weekend_days`, `with_header`, `on_day_click`.

## AgendaView (Mantine 9.4)

Vertical list of events grouped by date across a range.

```python
mn.agenda_view(
    events=events,
    range_start="2026-05-18",
    range_end="2026-05-24",
    on_event_click=State.on_event_click,
)
```

Props: `range_start`, `range_end`, `events`, `header_format`,
`date_header_format`, `render_event`, `on_event_click`, `locale`, `labels`,
`mode`.

> [Mantine docs — Schedule](https://mantine.dev/x/schedule/)
