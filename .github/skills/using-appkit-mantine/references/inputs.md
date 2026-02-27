# Inputs Reference

## Contents
- TextInput
- NumberInput
- PasswordInput
- Textarea
- TagsInput
- Select, MultiSelect, Autocomplete
- DateInput and date pickers
- MaskedInput
- JsonInput
- Checkbox, Radio, Switch
- Slider, RangeSlider

All input components inherit from `MantineInputComponentBase`. Common inherited props:
`label`, `description`, `error`, `required`, `with_asterisk`, `variant`, `size`, `radius`,
`value`, `default_value`, `placeholder`, `disabled`, `read_only`, `name`, `id`, `aria_label`,
`left_section`, `right_section`, `on_change`, `on_focus`, `on_blur`, `on_key_down`, `on_key_up`.

Plus all Mantine style props: `w`, `h`, `m*`, `p*`, `bg`, `c`, etc.

## TextInput

```python
mn.text_input(
    label="Username",
    placeholder="Enter username",
    value=State.username,
    on_change=State.set_username,
    required=True,
    left_section=rx.icon("user"),
    left_section_pointer_events="none",
    error=State.username_error,
)
```

Specific props: `with_error_styles`, `input_wrapper_order`.

## NumberInput

```python
mn.number_input(
    label="Price",
    value=State.price,
    on_change=State.set_price,
    min=0,
    max=1000,
    step=0.01,
    decimal_scale=2,
    prefix="$",
    thousand_separator=True,
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

Specific props: `min`, `max`, `step`, `clamp_behavior`, `decimal_scale`, `fixed_decimal_scale`,
`decimal_separator`, `allow_decimal`, `allow_negative`, `prefix`, `suffix`,
`thousand_separator`, `thousands_group_style`, `hide_controls`, `start_value`,
`with_keyboard_events`, `allow_mouse_wheel`.

## PasswordInput

```python
mn.password_input(
    label="Password",
    value=State.password,
    on_change=State.set_password,
    description="At least 8 characters",
    visible=State.show_password,
    on_visibility_change=State.toggle_password_visibility,
)
```

Specific props: `visible`, `default_visible`, `visibility_toggle_icon`,
`visibility_toggle_button_props`, `on_visibility_change`.

## Textarea

```python
mn.textarea(
    label="Bio",
    value=State.bio,
    on_change=State.set_bio,
    autosize=True,
    min_rows=3,
    max_rows=8,
)
```

**Cursor jumping**: With `value` + `on_change` (controlled), cursor jumps to end.
Use `default_value` + `on_blur` for production text areas.

Specific props: `rows`, `cols`, `wrap`, `autosize`, `min_rows`, `max_rows`, `resize`.

## TagsInput

```python
mn.tags_input(
    label="Skills",
    data=["React", "Python", "TypeScript"],
    value=State.tags,
    on_change=State.set_tags,
    max_tags=5,
    searchable=True,
)
```

**on_change receives `list[str]`** directly.

Specific props: `data`, `accept_value_on_blur`, `allow_duplicates`, `max_tags`,
`split_chars`, `clearable`, `on_search_change`, `on_duplicate`, `on_remove`.

## Select

```python
mn.select(
    label="Framework",
    data=["React", "Vue", "Angular"],
    value=State.framework,
    on_change=State.set_framework,
    searchable=True,
    clearable=True,
    nothing_found_message="Nothing found",
)
```

**on_change receives string value directly** (or `""` when null).

Data formats: `list[str]` or `list[dict]` with `value` and `label` keys.

Specific props: `allow_deselect`, `auto_select_on_blur`, `render_option`,
`select_first_option_on_change`.

## MultiSelect

```python
mn.multi_select(
    label="Technologies",
    data=["React", "Vue", "Angular", "Svelte"],
    value=State.selected,
    on_change=State.set_selected,
    searchable=True,
    clearable=True,
    max_values=3,
)
```

**on_change receives `list[str]`** directly.

Grouped data:
```python
data=[
    {"group": "Frontend", "items": ["React", "Vue"]},
    {"group": "Backend", "items": ["Django", "FastAPI"]},
]
```

Specific props: `max_values`, `hide_picked_options`, `with_check_icon`,
`clear_search_on_change`.

## Autocomplete

```python
mn.autocomplete(
    label="City",
    data=["New York", "London", "Tokyo"],
    value=State.city,
    on_change=State.set_city,
)
```

**on_change receives string value directly.** Data must be `list[str]` only.

## DateInput

```python
mn.date_input(
    label="Appointment",
    value=State.date,
    on_change=State.set_date,
    value_format="MM/DD/YYYY",
    clearable=True,
    min_date="2024-01-01",
    max_date="2025-12-31",
)
```

**on_change receives ISO date string or `""` when cleared.** Null is converted to empty string.

Specific props: `value_format`, `date_parser`, `fix_on_blur`, `clearable`,
`dropdown_type`, `min_date`, `max_date`, `locale`.

Other date components: `date_picker_input`, `date_time_picker`, `month_picker_input`,
`year_picker_input`, `time_input`, `time_picker`.

Inline pickers (no input): `calendar`, `mini_calendar`, `date_picker`, `month_picker`,
`year_picker`, `time_grid`.

## MaskedInput

```python
mn.masked_input(
    mask="+1 (000) 000-0000",
    label="Phone",
    placeholder="+1 (___) ___-____",
    on_accept=State.handle_phone,
)
```

**ALWAYS UNCONTROLLED** — never use `value` prop (prevents typing).
Use `on_accept` to capture values. Use `default_value` for initial values.

Specific props: `mask`, `definitions`, `blocks`, `lazy`, `placeholder_char`,
`overwrite`, `autofix`, `eager`, `unmask`, `on_accept`, `on_complete`.

## JsonInput

```python
mn.json_input(
    label="Config",
    value=State.json_value,
    on_change=State.set_json_value,
    format_on_blur=True,
    autosize=True,
    min_rows=4,
)
```

Specific props: `format_on_blur`, `validation_error`, `parser`, `pretty`,
`autosize`, `min_rows`, `max_rows`.

## Checkbox, Radio, Switch

```python
mn.checkbox(
    label="I agree",
    checked=State.agreed,
    on_change=State.set_agreed,
)

mn.switch(
    label="Dark mode",
    checked=State.dark_mode,
    on_change=State.set_dark_mode,
    size="md",
    color="teal",
)
```

**on_change receives `bool` (checked state)** via `event.target.checked`.

Common props: `checked`, `default_checked`, `label`, `description`, `error`,
`disabled`, `color`, `size`, `label_position`, `radius`, `name`, `value`.

## Slider and RangeSlider

```python
mn.slider(
    value=State.volume,
    on_change=State.set_volume,
    min=0,
    max=100,
    step=1,
    marks=[
        {"value": 0, "label": "0%"},
        {"value": 50, "label": "50%"},
        {"value": 100, "label": "100%"},
    ],
)

mn.range_slider(
    value=State.price_range,  # list[int | float]
    on_change=State.set_price_range,
    min=0,
    max=1000,
)
```

**on_change receives numeric value directly** (or list for RangeSlider).

Common props: `min`, `max`, `step`, `label`, `label_always_on`, `marks`,
`restrict_to_marks`, `color`, `size`, `radius`, `disabled`, `inverted`,
`on_change_end`.
