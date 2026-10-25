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
    with_events_drag_and_drop=True,
    can_drag_event=rx.Var("(event) => event.data?.draggable !== false"),
    with_event_resize=True,
    can_resize_event=rx.Var("(event) => !event.allDay"),
    recurrence_expansion_limit=100,
    on_event_click=State.open_event,  # receives event
    on_event_drop=State.move_event,
    on_event_resize=State.resize_event,
)
```

Predicates and render props (`can_drag_event`, `can_resize_event`,
`can_drop_event`, `render_event`, `render_event_body`, `render_day`,
`get_current_time`, `get_time_slot_props`, ...) run in the browser. Pass a
JavaScript function as `rx.Var("(event) => ...")`; a Python lambda does not
work. `mode="static"` makes every view read-only.

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
    day_view_props={"startTime": "08:00:00", "endTime": "20:00:00"},
    week_view_props={"firstDayOfWeek": 1, "weekendDays": [0, 6]},
    month_view_props={"maxEventsPerDay": 3},
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
  `mobile_month_view_props` — per-view prop dicts. Reflex passes dict keys to
  React unchanged, so write them in camelCase (`startTime`, not `start_time`).
- All shared event handlers (`on_event_click`, `on_event_drop`, etc.)
- Slot interaction: `with_drag_slot_select`, `on_slot_drag_end`,
  `on_time_slot_click`, `on_all_day_slot_click`, `on_day_click`,
  `on_external_event_drop`.

## DayView / WeekView (time-grid views)

Common props (in addition to shared props):

- `start_time` / `end_time` — visible window (`"HH:MM:SS"`).
- `interval_minutes` — slot height interval.
- `event_drag_interval` / `event_resize_interval` — snap step in minutes for
  drag and resize, independent of the grid (also on resources day/week).
- `with_interactive_background_events` — `display: "background"` events
  become clickable and fire `on_event_click`.
- `start_scroll_time` — initial scroll position.
- `slot_height`, `all_day_slot_height` — pixel sizes.
- `with_header`, `header_format`, `slot_label_format`.
- `with_current_time_indicator`, `with_current_time_bubble`, `with_all_day_slot`.
- `get_current_time` — JS function returning "now", for a timezone-aware
  current-time indicator.
- `with_sub_hour_grid_lines` — extra grid lines inside each hour.
- `with_agenda` — adds a toggle that switches to the agenda list.
- `highlight_business_hours`, `business_hours`.
- `event_overlap_mode` (`"columns"` | `"cascade"`), `event_overlap_raise_delay`
  (ms before a hovered cascaded event comes to the front, default 600).
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
- `max_events_per_day`, `with_weekend_days` (`False` hides weekend columns),
  `with_agenda`.
- `with_drag_slot_select`, `on_slot_drag_end`, `on_external_event_drop`,
  `get_day_props`, `get_week_number_props`, `on_week_number_click`,
  `scroll_area_props`, `on_day_click`, `on_date_change`, `on_view_change`.

## YearView

Renders 12 mini-months. Props: shared props plus
`first_day_of_week`, `weekend_days`, `highlight_today`, `with_outside_days`,
`with_week_numbers`, `on_day_click`, `on_month_click`, plus:

- `render_day` — render-prop for fully custom day cell content; receives the day
  date (`YYYY-MM-DD`) and that day's events.
- `with_weekend_days=False` — hide weekend day columns; which days count as
  weekend is controlled by `weekend_days` (default `[0, 6]`).

```python
mn.schedule.year_view(
    events=State.events,
    date="2026-05-21",
    with_weekend_days=False,
)
```

## MobileMonthView

Stacked agenda layout for narrow viewports. Props: shared props plus
`first_day_of_week`, `with_outside_days`, `on_day_click`, `on_date_change`.

## Resource views

Resource-oriented views render resources (rooms, people, equipment) as **rows**
and time as **columns**. Each resource is `{id, label}`; events reference a
resource via `resourceId`.

```python
resources = [
    {"id": "tokyo", "label": "Room: Tokyo"},
    {"id": "paris", "label": "Room: Paris"},
]
events = [
    {
        "id": "1",
        "title": "Standup",
        "start": "2026-05-21 09:00:00",
        "end": "2026-05-21 09:30:00",
        "resourceId": "tokyo",
        "color": "blue",
    }
]

# Unified wrapper (day / week / month switching)
mn.resources_schedule(
    resources=resources,
    events=events,
    date=State.date,
    on_date_change=State.set_date,
    view=State.view,
    on_view_change=State.set_view,
    day_view_props={"startTime": "08:00:00", "endTime": "18:00:00"},
)

# Individual views
mn.resources_day_view(
    resources=resources,
    events=events,
    date="2026-05-21",
    start_time="08:00:00",
    end_time="18:00:00",
)
mn.resources_week_view(resources=resources, events=events, date="2026-05-21")
mn.resources_month_view(
    resources=resources, events=events, date="2026-05-21", with_weekend_days=False
)
```

Shared props: `resources`, `events`, `date`, `on_date_change`, `groups`,
`group_label_width`, `render_resource_label`, `mode` (`"static"` = read-only),
`with_events_drag_and_drop`, `with_event_resize`, `on_event_click`,
`on_event_drop`, `on_time_slot_click`. Day/Week add `start_time`, `end_time`,
`interval_minutes`, `slot_width`, `row_height`, `with_current_time_indicator`.
Month adds `day_width`, `with_weekend_days`, `with_header`, `on_day_click`.

- `interval_minutes` (Day/Week) accepts values over 60 — any whole number of
  hours (e.g. `120`, `240`) renders multi-hour time slots.
- `ResourcesMonthView` resizes events via `with_event_resize` /
  `can_resize_event` / `on_event_resize` (payload: `{eventId, newStart,
  newEnd}`). Resizing snaps to whole days, keeps the event's time of day,
  and cannot cross resources.

## Overlap rules and drop validation (all views)

`prevent_event_overlap=True` rejects moves and resizes that would overlap
another event. For custom rules pass JS predicates that return `False` to
reject: `can_drop_event` and `can_resize_event_to` receive
`{event, start, end, resourceId?}`, `can_drop_external_event` does the same check
for items dragged in from outside. `on_event_placement_rejected` receives
`{action, event, start, end, conflicts, reason, resourceId?}` with `action`
`"drop"` | `"resize"` | `"external-drop"` and `reason` `"overlap"` |
`"rejected"`. Invalid targets get
`data-invalid` while hovered, so you can style them.

```python
mn.schedule.week_view(
    events=State.events,
    with_events_drag_and_drop=True,
    prevent_event_overlap=True,
    can_drop_event=rx.Var("({ start }) => new Date(start).getDay() !== 0"),
    on_event_placement_rejected=State.on_rejected,
)
```

## AgendaView

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
