# Inputs — Date & Time

## Contents

- DateInput
- DatePickerInput (range / multiple)
- DateTimePicker
- MonthPickerInput / YearPickerInput
- TimeInput
- TimePicker
- TimeGrid
- InlineDateTimePicker
- Inline pickers (Calendar, DatePicker, MonthPicker, YearPicker, MiniCalendar)

All date/time inputs inherit from `MantineInputComponentBase`. Values are exchanged as ISO
strings (`"YYYY-MM-DD"`, `"HH:MM"`) or `""` when cleared.

## DateInput

Single-date text input with an inline popover calendar.

```python
mn.date_input(
    label="Appointment",
    default_value="",  # ISO string; use value= for controlled
    placeholder="Pick a date",
    value_format="DD.MM.YYYY",  # display format (default: "MMMM D, YYYY")
    clearable=True,
    min_date="2024-01-01",
    max_date="2025-12-31",
    on_change=State.set_date,
)
```

**on_change receives ISO date string or `""` when cleared.**

Props: `value_format`, `date_parser`, `fix_on_blur`, `clearable`,
`dropdown_type` (`"popover"` | `"modal"`), `min_date`, `max_date`, `locale`.

> [Mantine docs — DateInput](https://mantine.dev/dates/date-input/)

## DatePickerInput

Popover-based picker with optional range or multiple-date mode.

```python
# Single date (uncontrolled)
mn.date_picker_input(
    label="Date",
    placeholder="Pick date",
    clearable=True,
)

# Date range — on_change receives [start_iso, end_iso] or ["", ""]
mn.date_picker_input(
    label="Period",
    placeholder="Pick range",
    type="range",
    clearable=True,
    number_of_columns=2,  # show two months side by side
    on_change=State.set_range,
    presets=[
        {"label": "Last 7 days", "value": ["2025-05-14", "2025-05-21"]},
        {"label": "This month", "value": ["2025-05-01", "2025-05-31"]},
    ],
)

# Multiple independent dates
mn.date_picker_input(
    label="Dates",
    type="multiple",
    clearable=True,
)
```

Props: `type` (`"default"` | `"range"` | `"multiple"`), `number_of_columns`,
`hide_outside_dates`, `first_day_of_week`, `weekend_days`, `presets`, `value_formatter`.

> [Mantine docs — DatePickerInput](https://mantine.dev/dates/date-picker-input/)

## DateTimePicker

Combined date + time picker in a single popover.

```python
mn.date_time_picker(
    label="Meeting time",
    placeholder="Pick date and time",
    clearable=True,
    on_change=State.set_datetime,
)
```

> [Mantine docs — DateTimePicker](https://mantine.dev/dates/date-time-picker/)

## MonthPickerInput / YearPickerInput

```python
mn.month_picker_input(
    label="Month",
    placeholder="Pick a month",
    presets=[
        {"label": "This month", "value": "2025-05-01"},
        {"label": "Last month", "value": "2025-04-01"},
    ],
)

mn.year_picker_input(label="Year", placeholder="Pick a year")
```

> [Mantine docs — MonthPickerInput](https://mantine.dev/dates/month-picker/) ·
> [YearPickerInput](https://mantine.dev/dates/year-picker/)

## TimeInput

Native time input field with browser chrome.

```python
mn.time_input(
    label="Start time",
    with_seconds=True,
    on_change=State.set_time,
)
```

> [Mantine docs — TimeInput](https://mantine.dev/dates/time-input/)

## TimePicker

Popover-based time picker with separate hour/minute/second spinners and optional AM/PM toggle.

```python
mn.time_picker(
    label="Meeting time",
    placeholder="Pick time",
    with_seconds=True,
    on_change=State.set_time,
)

# Duration mode — allows values beyond 24h
mn.time_picker(
    label="Duration",
    type="duration",
    with_seconds=True,
)
```

Props: `with_seconds`, `type` (`"duration"` enables durations > 24h), plus all
`MantineInputComponentBase` props.

> [Mantine docs — TimePicker](https://mantine.dev/dates/time-picker/)

## TimeGrid

Inline slot picker — displays a grid of selectable time slots.

```python
mn.time_grid(
    data=["09:00", "10:00", "11:00", "12:00", "14:00"],
    on_change=State.set_slot,
)
```

> [Mantine docs — TimeGrid](https://mantine.dev/dates/time-grid/)

## InlineDateTimePicker

Inline calendar + time picker without a popover trigger — renders directly on the page.

```python
mn.inline_date_time_picker(
    value=State.scheduled_at,
    on_change=State.set_scheduled_at,
    type="default",  # "default" | "multiple" | "range"
    min_date="2024-01-01",
    max_date="2030-12-31",
    with_seconds=False,
    first_day_of_week=1,  # 0 Sun, 1 Mon
    highlight_today=True,
    number_of_columns=1,
    submit_button_props={"children": "Apply"},
)
```

Props: `type`, `value`, `default_value`, `size`, `full_width`, `number_of_columns`,
`max_date`, `min_date`, `allow_deselect`, `allow_single_date_in_range`,
`hide_outside_dates`, `hide_weekdays`, `highlight_today`, `with_cell_spacing`,
`with_week_numbers`, `with_seconds`, `first_day_of_week`, `time_picker_props`,
`end_time_picker_props`, `submit_button_props`, `default_time_value`,
`on_change`, `on_submit`, `on_level_change`, `on_date_change`.

> [Mantine docs — InlineDateTimePicker](https://mantine.dev/dates/inline-date-time-picker/)

## Inline pickers (no input field)

Render directly on the page without a dropdown:

```python
mn.center(
    mn.date_picker(
        type="range",
        number_of_columns=2,
        on_change=State.set_range,
    )
)
```

Available inline components: `mn.calendar()`, `mn.date_picker()`, `mn.month_picker()`,
`mn.year_picker()`, `mn.mini_calendar()`, `mn.time_grid()`.
