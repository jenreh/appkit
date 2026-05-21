# Inputs — Text & Freeform

## Contents

- Form (input sub-components)
- TextInput
- NumberInput
- PasswordInput
- Textarea
- MaskedInput
- JsonInput

All input components inherit from `MantineInputComponentBase`. Common inherited props:
`label`, `description`, `error`, `required`, `with_asterisk`, `variant`, `size`, `radius`,
`value`, `default_value`, `placeholder`, `disabled`, `read_only`, `name`, `id`, `aria_label`,
`left_section`, `right_section`, `on_change`, `on_focus`, `on_blur`, `on_key_down`, `on_key_up`.

**Controlled vs uncontrolled**: prefer `default_value` (uncontrolled) unless the component must
react to external state changes. Pair `value` with `on_change` only when you need two-way binding.

## Form (input sub-components)

`mn.form` is a namespace giving direct access to Mantine's low-level input building blocks.

| Component | Description |
| --- | --- |
| `mn.form.text` | Alias for `mn.text_input` |
| `mn.form.number` | Alias for `mn.number_input` |
| `mn.form.password` | Alias for `mn.password_input` |
| `mn.form.masked` | Alias for `mn.masked_input` |
| `mn.form.textarea` | Alias for `mn.textarea` |
| `mn.form.json` | Alias for `mn.json_input` |
| `mn.form.date` | Alias for `mn.date_input` |
| `mn.form.tags` | Alias for `mn.tags_input` |

Use the sub-components when assembling custom input layouts that don't fit the standard
`MantineInputComponentBase` wrapper (e.g., side-by-side label + description, custom error placement).

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
    default_value=9.99,
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
