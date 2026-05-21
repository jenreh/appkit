# Inputs Reference

## Contents

- TextInput
- NumberInput
- PasswordInput
- Textarea
- TagsInput
- Select, MultiSelect, Autocomplete
- DateInput and date pickers
- TimeInput, TimePicker, TimeGrid
- MaskedInput
- JsonInput
- Checkbox, CheckboxGroup, CheckboxCard
- Radio, RadioGroup, RadioCard
- Switch
- Slider, RangeSlider
- SegmentedControl
- RichSelect
- Form (input sub-components)

All input components inherit from `MantineInputComponentBase`. Common inherited props:
`label`, `description`, `error`, `required`, `with_asterisk`, `variant`, `size`, `radius`,
`value`, `default_value`, `placeholder`, `disabled`, `read_only`, `name`, `id`, `aria_label`,
`left_section`, `right_section`, `on_change`, `on_focus`, `on_blur`, `on_key_down`, `on_key_up`.

Plus all Mantine style props: `w`, `h`, `m*`, `p*`, `bg`, `c`, etc.

**Controlled vs uncontrolled**: prefer `default_value` (uncontrolled) unless the component must
react to external state changes. Pair `value` with `on_change` only when you need two-way binding.

## Form (input sub-components)

`mn.form` is a namespace giving direct access to Mantine's low-level input building blocks.

| Component | Description |
| `mn.form.text` | Alias for `mn.text_input` |
| `mn.form.number` | Alias for `mn.number_input` |
| `mn.form.password` | Alias for `mn.password_input` |
| `mn.form.masked` | Alias for `mn.masked_input` |
| `mn.form.textarea` | Alias for `mn.textarea` |
| `mn.form.json` | Alias for `mn.json_input` |
| `mn.form.date` | Alias for `mn.date_input` |
| `mn.form.tags` | Alias for `mn.tags_input` |

Use the subcompponents when assembling custom input layouts that don't fit the standard `MantineInputComponentBase`
wrapper (e.g., side-by-side label + description, custom error placement).

| Sub-component | Description |
| --- | --- |
| `mn.form.wrapper` | `InputWrapper` — outer container with label/description/error slots |
| `mn.form.label` | `InputLabel` — standalone label element |
| `mn.form.description` | `InputDescription` — helper text below the label |
| `mn.form.error` | `InputError` — styled error message |
| `mn.form.placeholder` | `InputPlaceholder` — placeholder element |
| `mn.form.clear_button` | `InputClearButton` — clear icon button inside an input |
| `mn.form.input` | `Input` — bare unstyled input (no label/description wrapper) |

```python
# Custom input layout with manual label/description/error
mn.form.wrapper(
    mn.form.label("Start Date", required=True),
    mn.form.description("Must be in the future"),
    mn.date_input(placeholder="Pick a date"),
    mn.form.error(State.date_error),
)
```

> [Mantine docs — Input](https://mantine.dev/core/input/)

## TextInput

```python
# Uncontrolled — preferred for simple inputs that don't need live state binding
mn.text_input(
    label="Username",
    placeholder="Enter username",
    default_value="",
    required=True,
    left_section=rx.icon("user"),
    left_section_pointer_events="none",
    error=State.username_error,
)

# Controlled — two-way binding to state
mn.text_input(
    label="Username",
    value=State.username,
    on_change=State.set_username,
)
```

Props: `with_error_styles`, `input_wrapper_order`.

> [Mantine docs — TextInput](https://mantine.dev/core/text-input/)

## NumberInput

```python
mn.number_input(
    label="Price",
    default_value=9.99,  # use value=State.price for controlled
    min=0,
    max=1000,
    step=0.01,
    decimal_scale=2,
    fixed_decimal_scale=True,
    prefix="$",
    thousand_separator=True,
    on_change=State.set_price,
)
```

**on_change receives raw number or empty string `""`**, not an event object.

Handler pattern:

```python
def set_price(self, val: float | str) -> None:
    if val == "":
        self.price = 0.0
        return
    with contextlib.suppress(ValueError):
        self.price = float(val)
```

Props: `min`, `max`, `step`, `clamp_behavior`, `decimal_scale`, `fixed_decimal_scale`,
`decimal_separator`, `allow_decimal`, `allow_negative`, `prefix`, `suffix`,
`thousand_separator`, `thousands_group_style`, `hide_controls`, `start_value`,
`with_keyboard_events`, `allow_mouse_wheel`.

> [Mantine docs — NumberInput](https://mantine.dev/core/number-input/)

## PasswordInput

```python
mn.password_input(
    label="Password",
    placeholder="Enter password",
    description="At least 8 characters",
    on_change=State.set_password,
    visible=State.show_password,
    on_visibility_change=State.toggle_password_visibility,
    left_section=rx.icon("lock", size=16),
    left_section_pointer_events="none",
)
```

Props: `visible`, `default_visible`, `visibility_toggle_icon`,
`visibility_toggle_button_props`, `on_visibility_change`.

> [Mantine docs — PasswordInput](https://mantine.dev/core/password-input/)

## Textarea

```python
mn.textarea(
    label="Bio",
    default_value="",  # avoids cursor-jump bug present with controlled mode
    on_blur=State.save_bio,  # capture on blur instead of on each keystroke
    placeholder="Tell us about yourself",
    autosize=True,
    min_rows=3,
    max_rows=8,
    resize="none",
)
```

**Cursor jumping**: With `value` + `on_change` (controlled), the cursor jumps to the end on every
keystroke because Reflex re-renders the whole DOM node. Always prefer `default_value` + `on_blur`
for text areas.

Props: `rows`, `cols`, `wrap`, `autosize`, `min_rows`, `max_rows`, `resize`
(`"none"` | `"vertical"` | `"horizontal"` | `"both"`).

> [Mantine docs — Textarea](https://mantine.dev/core/textarea/)

## TagsInput

```python
mn.tags_input(
    label="Skills",
    data=["React", "Python", "TypeScript"],
    default_value=["Python"],  # pre-selected tags
    placeholder="Add a skill",
    max_tags=5,
    allow_new=False,  # only allow values from data list
    on_change=State.set_tags,
)
```

**on_change receives `list[str]`** directly.

Props: `data`, `accept_value_on_blur`, `allow_duplicates`, `allow_new`,
`max_tags`, `split_chars`, `clearable`, `on_search_change`, `on_duplicate`, `on_remove`.

> [Mantine docs — TagsInput](https://mantine.dev/core/tags-input/)

## Select

```python
mn.select(
    label="Framework",
    data=["React", "Vue", "Angular"],
    default_value="React",  # use value=State.x for controlled
    searchable=True,
    clearable=True,
    nothing_found_message="No match",
    on_change=State.set_framework,
)
```

**on_change receives string value directly** (or `""` when null/cleared).

Data formats: `list[str]` or `list[dict]` with `value` and `label` keys.

Grouped data:

```python
data = [
    {"group": "Frontend", "items": ["React", "Vue"]},
    {"group": "Backend", "items": ["Django", "FastAPI"]},
]
```

Props: `allow_deselect`, `auto_select_on_blur`, `render_option`,
`select_first_option_on_change`, `with_check_icon`, `check_icon_position`.

> [Mantine docs — Select](https://mantine.dev/core/select/)

## MultiSelect

```python
mn.multi_select(
    label="Technologies",
    data=["React", "Vue", "Angular", "Svelte"],
    default_value=["React"],  # use value=State.x for controlled
    searchable=True,
    clearable=True,
    max_values=3,
    on_change=State.set_selected,
)
```

**on_change receives `list[str]`** directly.

Grouped data:

```python
data = [
    {"group": "Frontend", "items": ["React", "Vue"]},
    {"group": "Backend", "items": ["Django", "FastAPI"]},
]
```

Props: `max_values`, `hide_picked_options`, `with_check_icon`, `check_icon_position`,
`clear_search_on_change`.

> [Mantine docs — MultiSelect](https://mantine.dev/core/multi-select/)

## Autocomplete

```python
mn.autocomplete(
    label="City",
    data=["New York", "London", "Tokyo"],
    placeholder="Start typing...",
    on_change=State.set_city,
)
```

**on_change receives string value directly.** Unlike Select, the user can type any value — data
provides suggestions only. Data must be `list[str]`.

Props: `limit`, `filter`, `render_option`, `dropdown_opened`, `on_dropdown_open`,
`on_dropdown_close`, `on_option_submit`.

> [Mantine docs — Autocomplete](https://mantine.dev/core/autocomplete/)

## DateInput

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

### DatePickerInput

Popover-based picker with optional range mode.

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

### DateTimePicker

```python
mn.date_time_picker(
    label="Meeting time",
    placeholder="Pick date and time",
    clearable=True,
    on_change=State.set_datetime,
)
```

> [Mantine docs — DateTimePicker](https://mantine.dev/dates/date-time-picker/)

### MonthPickerInput / YearPickerInput

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

### TimeInput

```python
mn.time_input(
    label="Start time",
    with_seconds=True,
    on_change=State.set_time,
)
```

> [Mantine docs — TimeInput](https://mantine.dev/dates/time-input/)

### TimePicker

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

### TimeGrid

Inline slot picker — displays a grid of selectable time slots.

```python
mn.time_grid(
    data=["09:00", "10:00", "11:00", "12:00", "14:00"],
    on_change=State.set_slot,
)
```

> [Mantine docs — TimeGrid](https://mantine.dev/dates/time-grid/)

### Inline pickers (no input field)

Render directly on page without a dropdown:
`mn.calendar()`, `mn.date_picker()`, `mn.month_picker()`, `mn.year_picker()`,
`mn.mini_calendar()`, `mn.time_grid()`.

```python
mn.center(
    mn.date_picker(
        type="range",
        number_of_columns=2,
        on_change=State.set_range,
    )
)
```

## MaskedInput

```python
mn.masked_input(
    label="Phone number",
    mask="(999) 999-9999",  # 9=digit  a=letter  *=any char
    placeholder="(___) ___-____",
    default_value="",
    on_accept=State.handle_phone,
)
```

**ALWAYS UNCONTROLLED** — never use `value` prop (prevents typing). Use `default_value` for
initial display. Use `on_accept` (fires when input matches the full mask) to capture values.

Props: `mask`, `definitions` (custom char→regex map), `blocks` (named block patterns),
`lazy`, `placeholder_char`, `overwrite`, `autofix`, `eager`, `unmask`, `on_accept`,
`on_complete`.

## JsonInput

```python
mn.json_input(
    label="Config",
    default_value="{}",
    on_change=State.set_json_value,
    on_blur=State.validate_json,
    validation_error=State.json_error,
    format_on_blur=True,
    autosize=True,
    min_rows=4,
)
```

Props: `format_on_blur`, `validation_error`, `parser`, `pretty`,
`autosize`, `min_rows`, `max_rows`.

> [Mantine docs — JsonInput](https://mantine.dev/core/json-input/)

## Checkbox, CheckboxGroup, CheckboxCard

Single checkbox:

```python
mn.checkbox(
    label="I agree to the terms",
    default_checked=False,
    on_change=State.set_agreed,
    indeterminate=State.partial_select,  # shows dash icon
    color="blue",
    size="md",
    radius="sm",
)
```

**on_change receives `bool`** (checked state).

Props: `checked`, `default_checked`, `indeterminate`, `label`, `description`, `error`,
`disabled`, `color`, `size`, `label_position`, `radius`, `name`, `value`, `icon_color`.

Group of checkboxes — use `mn.checkbox.group(...)` (on_change → `list[str]`):

```python
mn.checkbox.group(
    mn.checkbox(value="react", label="React"),
    mn.checkbox(value="vue", label="Vue"),
    mn.checkbox(value="svelte", label="Svelte"),
    label="Frameworks",
    default_value=["react"],
    on_change=State.set_frameworks,
    max_selected_values=2,
)
```

Card-style checkbox — use `mn.checkbox.card(...)` with `mn.checkbox.indicator()`:

```python
mn.checkbox.card(
    mn.stack(
        mn.checkbox.indicator(),
        mn.text("Pro Plan", fw=500),
        mn.text("$29/mo", size="sm", c="dimmed"),
    ),
    value="pro",
    checked=State.plan == "pro",
    on_change=lambda _: State.set_plan("pro"),
    radius="md",
    p="md",
    with_border=True,
)
```

> [Mantine docs — Checkbox](https://mantine.dev/core/checkbox/)

## Radio, RadioGroup, RadioCard

RadioGroup — use `mn.radio.group(...)` (on_change → `str`):

```python
mn.radio.group(
    mn.radio(value="monthly", label="Monthly"),
    mn.radio(value="yearly", label="Yearly — save 20%"),
    label="Billing cycle",
    default_value="monthly",
    on_change=State.set_billing,
)
```

**on_change receives the selected `str` value directly.**

Individual Radio props: `value`, `label`, `description`, `disabled`, `color`, `size`, `icon_color`.

Card-style radio — use `mn.radio.card(...)` with `mn.radio.indicator()`:

```python
mn.radio.card(
    mn.stack(
        mn.radio.indicator(),
        mn.text("Starter", fw=500),
        mn.text("Free forever", size="sm", c="dimmed"),
    ),
    value="starter",
    checked=State.plan == "starter",
    on_change=lambda _: State.set_plan("starter"),
    radius="md",
    p="md",
)
```

> [Mantine docs — Radio](https://mantine.dev/core/radio/)

## Switch

Toggle switch.

```python
mn.switch(
    label="Dark mode",
    default_checked=False,
    on_change=State.set_dark_mode,
    size="md",
    color="teal",
    on_label="ON",
    off_label="OFF",
    thumb_icon=rx.icon("sun", size=12),
)
```

**on_change receives `bool`** (checked state).

Props: `checked`, `default_checked`, `label`, `description`, `error`, `disabled`,
`color`, `size`, `label_position`, `radius`, `on_label`, `off_label`, `thumb_icon`.

> [Mantine docs — Switch](https://mantine.dev/core/switch/)

## Slider and RangeSlider

```python
mn.slider(
    default_value=50,
    min=0,
    max=100,
    step=1,
    start_point_value=0,  # value where the filled track starts
    marks=[
        {"value": 0, "label": "0%"},
        {"value": 50, "label": "50%"},
        {"value": 100, "label": "100%"},
    ],
    on_change=State.set_volume,
    on_change_end=State.commit_volume,  # fires only on mouse release
)

mn.range_slider(
    default_value=[20, 80],  # list[int | float]
    min=0,
    max=1000,
    min_range=10,  # minimum gap between the two thumbs
    on_change=State.set_price_range,
)
```

**on_change receives numeric value directly** (or `list` for RangeSlider).

Common props: `min`, `max`, `step`, `label`, `label_always_on`, `marks`,
`restrict_to_marks`, `start_point_value`, `color`, `size`, `radius`, `disabled`,
`inverted`, `on_change_end`.

RangeSlider-specific: `min_range`, `max_range`.

> [Mantine docs — Slider](https://mantine.dev/core/slider/)

## SegmentedControl

Tab-like selector that returns a string value.

```python
mn.segmented_control(
    data=["React", "Vue", "Angular"],
    default_value="React",
    on_change=State.set_framework,
    color="blue",
    size="md",
    radius="md",
    full_width=True,
    orientation="horizontal",
    auto_contrast=True,
    transition_duration=200,
    transition_timing_function="ease",
    with_items_borders=True,
)
```

**on_change receives the selected `str` value directly.**

Data formats: `list[str]` or `list[dict]` with `"label"` and `"value"` keys (also supports `"disabled"`).

```python
mn.segmented_control(
    data=[
        {"label": "Monthly", "value": "monthly"},
        {"label": "Yearly (-20%)", "value": "yearly"},
    ],
    default_value="monthly",
    on_change=State.set_billing,
)
```

Props: `data`, `value`, `default_value`, `on_change`, `color`, `size`, `radius`,
`orientation` (`"horizontal"` | `"vertical"`), `full_width`, `read_only`,
`auto_contrast`, `transition_duration`, `transition_timing_function`, `with_items_borders`.

> [Mantine docs — SegmentedControl](https://mantine.dev/core/segmented-control/)

## RichSelect

Advanced combobox with custom option rendering, creatable options, and multi-select support.
Use when `mn.select` or `mn.multi_select` don't offer enough flexibility.

```python
data = [
    {"value": "react", "label": "React", "description": "UI library", "emoji": "⚛️"},
    {
        "value": "vue",
        "label": "Vue",
        "description": "Progressive framework",
        "emoji": "💚",
    },
]


def render_option(row: dict) -> rx.Component:
    return mn.group(
        mn.text(row.get("emoji", ""), w="24px"),
        mn.stack(
            mn.text(row["label"], fw=500),
            mn.text(row.get("description", ""), size="xs", c="dimmed"),
            gap=0,
        ),
        gap="xs",
    )


mn.rich_select(
    mn.rich_select.map(data, renderer=render_option),
    placeholder="Pick a framework",
    searchable=True,
    clearable=True,
    value=State.selected,
    on_change=State.set_selected,
)
```

**on_change receives the selected `str` value directly.**

For multi-select mode, pass `values=State.selected_list` and on_change receives `list[str]`.

Creatable (allow user to add new options):

```python
mn.rich_select(
    mn.rich_select.map(State.options, renderer=render_option),
    creatable=True,
    on_create=State.add_option,  # receives the new value string
    searchable=True,
    placeholder="Select or create...",
    on_change=State.set_value,
)
```

Props: `searchable`, `clearable`, `creatable`, `search_placeholder`, `nothing_found`,
`max_dropdown_height`, `position`, `value`, `values` (multi-select list),
`on_change`, `on_create`, `on_search_change`, `on_clear`, `on_opened_change`.
