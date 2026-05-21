# Inputs — Toggles & Choice

## Contents

- Checkbox, CheckboxGroup, CheckboxCard
- Radio, RadioGroup, RadioCard
- Switch
- Chip, ChipGroup
- SegmentedControl
- Fieldset

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

## Chip and Chip.Group

Single chip (toggle-button style) or group of chips for multi-/single-select.

```python
mn.chip("Important", value="important", color="red", variant="filled")

mn.chip.group(
    mn.group(
        mn.chip("Frontend", value="frontend"),
        mn.chip("Backend", value="backend"),
        mn.chip("DevOps", value="devops"),
    ),
    value=State.tags,  # str (single) or list[str] (multiple)
    multiple=True,
    on_change=State.set_tags,
)
```

Chip props: `value`, `checked`, `default_checked`, `color`, `variant`
(`"outline"`, `"filled"`, `"light"`), `size`, `radius`, `icon`, `wrapper_props`,
`autocontrast`, `disabled`, `id`, `name`, `type` (`"checkbox"` | `"radio"`), `on_change`
(receives `bool` when used standalone).

Chip.Group props: `multiple`, `value`, `default_value`, `on_change`
(receives `str` for single, `list[str]` for multiple).

> [Mantine docs — Chip](https://mantine.dev/core/chip/)

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
)
```

**on_change receives the selected `str` value directly.**

Data formats: `list[str]` or `list[dict]` with `"label"` and `"value"` keys (also supports `"disabled"`):

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

## Fieldset

Groups related inputs with an optional legend.

```python
mn.fieldset(
    mn.stack(
        mn.text_input(label="First name"),
        mn.text_input(label="Last name"),
    ),
    legend="Personal information",
    variant="filled",  # "default" | "filled" | "unstyled"
    radius="md",
    disabled=False,
)
```

Props: `legend`, `variant`, `radius`, `disabled`.

> [Mantine docs — Fieldset](https://mantine.dev/core/fieldset/)
