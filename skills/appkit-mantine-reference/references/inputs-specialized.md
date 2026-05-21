# Inputs — Specialized

## Contents

- Slider, RangeSlider
- FileInput
- PinInput
- Rating
- ColorInput
- ColorPicker
- HueSlider / AlphaSlider
- AngleSlider

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

## FileInput

Button-style file picker. Use `mn.dropzone` (extensions.md) for drag-and-drop.

```python
mn.file_input(
    label="Upload document",
    placeholder="Click to select file",
    accept="image/png,image/jpeg",  # MIME types
    multiple=False,
    clearable=True,
    value=State.uploaded_file,
    on_change=State.handle_file,  # receives a File object (or list when multiple)
)
```

Props: `value`, `default_value`, `accept`, `multiple`, `capture`, `clearable`,
`clear_button_props`, `file_input_props`, `value_component`, `placeholder`,
`label`, `description`, `error`, `required`, `disabled`, `radius`, `size`,
`left_section`, `right_section`, `with_asterisk`, `name`, `form`, `on_change`.

> [Mantine docs — FileInput](https://mantine.dev/core/file-input/)

## PinInput

Multi-character PIN / OTP code entry.

```python
mn.pin_input(
    length=6,
    type="number",  # "number" | "alphanumeric" | regex
    placeholder="·",
    mask=True,  # hides characters like password
    one_time_code=True,  # autocomplete="one-time-code" for SMS OTP
    value=State.otp,
    on_change=State.set_otp,  # receives str on each change
    on_complete=State.verify_otp,  # receives str when all chars filled
)
```

Props: `length`, `type` (`"number"`, `"alphanumeric"`, or regex), `mask`,
`one_time_code`, `placeholder`, `value`, `default_value`, `name`, `form`,
`autofocus`, `disabled`, `error`, `inputmode`, `size`, `radius`, `gap`,
`input_type`, `manage_focus`, `on_change`, `on_complete` (both receive `str`).

> [Mantine docs — PinInput](https://mantine.dev/core/pin-input/)

## Rating

Star rating input.

```python
mn.rating(
    value=State.rating,
    on_change=State.set_rating,  # receives float
    count=5,
    fractions=2,  # half-stars
    size="lg",
    color="yellow",
    readonly=False,
    highlight_selected_only=False,
)
```

Props: `value`, `default_value`, `count`, `fractions` (segments per item, e.g. 2 = half),
`size`, `color`, `readonly`, `highlight_selected_only`, `empty_symbol`, `full_symbol`,
`name`, `on_change`, `on_hover` (receives `float`), `on_hover_end`.

> [Mantine docs — Rating](https://mantine.dev/core/rating/)

## ColorInput

Text input + swatch + popover color picker.

```python
mn.color_input(
    label="Brand color",
    value=State.color,
    on_change=State.set_color,  # receives str (hex/rgba)
    on_change_end=State.persist_color,  # receives str when commit
    format="hex",  # "hex" | "rgba" | "hsla" | "hsl" | "rgb"
    swatches=["#fa5252", "#fd7e14", "#fab005", "#2f9e44", "#1971c2"],
    disallow_input=False,
    with_eye_dropper=True,
    with_picker=True,
    fix_on_blur=True,
    close_on_color_swatch_click=False,
)
```

Props: `format`, `swatches`, `swatches_per_row`, `disallow_input`, `fix_on_blur`,
`with_eye_dropper`, `with_picker`, `with_preview`, `picker_type`,
`popover_props`, `close_on_color_swatch_click`, `eye_dropper_icon`,
`left_section`, `right_section`, `label`, `description`, `error`, `placeholder`,
`size`, `radius`, `disabled`, `required`, `with_asterisk`, `value`, `default_value`,
`on_change`, `on_change_end`.

> [Mantine docs — ColorInput](https://mantine.dev/core/color-input/)

## ColorPicker

Standalone color picker (no input field).

```python
mn.color_picker(
    value=State.color,
    on_change=State.set_color,
    format="hex",
    swatches=["#fa5252", "#fab005", "#1971c2"],
    swatches_per_row=10,
    full_width=False,
    size="md",
)
```

Props: `format`, `swatches`, `swatches_per_row`, `full_width`, `size`, `saturation_label`,
`hue_label`, `alpha_label`, `focusable`, `with_picker`, `value`, `default_value`,
`on_change`, `on_change_end`.

> [Mantine docs — ColorPicker](https://mantine.dev/core/color-picker/)

## HueSlider / AlphaSlider

Standalone slider primitives for building custom color UIs.

```python
mn.hue_slider(
    value=State.hue,
    on_change=State.set_hue,  # receives float (0-360)
    on_change_end=State.commit_hue,
    size="sm",
)

mn.alpha_slider(
    color="#ff0000",
    value=State.alpha,
    on_change=State.set_alpha,  # receives float (0-1)
    size="sm",
)
```

HueSlider props: `value`, `on_change`, `on_change_end`, `size`, `focusable`.

AlphaSlider props: `value`, `color` (base color for transparency preview),
`on_change`, `on_change_end`, `size`, `focusable`.

> [Mantine docs — Color Picker primitives](https://mantine.dev/core/color-picker/)

## AngleSlider

Circular slider for picking an angle (0–360°). Useful for rotation, direction, gradient angle.

```python
mn.angle_slider(
    value=State.angle,
    on_change=State.set_angle,  # receives int (0-360)
    on_change_end=State.commit_angle,
    size=120,
    thumb_size=12,
    marks=[
        {"value": 0, "label": "N"},
        {"value": 90, "label": "E"},
        {"value": 180, "label": "S"},
        {"value": 270, "label": "W"},
    ],
    with_label=True,
    step=1,
    format_label=lambda v: f"{v}°",
)
```

Props: `value`, `default_value`, `size`, `thumb_size`, `step`, `marks`, `with_label`,
`format_label`, `restrict_to_marks`, `disabled`, `aria_label`, `name`, `hidden_input_props`,
`thumb_props`, `on_change`, `on_change_end`, `on_mouse_down`, `on_scrub_start`, `on_scrub_end`.

> [Mantine docs — AngleSlider](https://mantine.dev/core/angle-slider/)
