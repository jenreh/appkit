# Feedback & Status Reference

## Contents

- Alert
- Notification
- Progress
- RingProgress
- SemiCircleProgress
- Loader
- Skeleton

## Alert

```python
mn.alert(
    "This is an important message",
    title="Warning",
    color="yellow",
    variant="light",
    icon=rx.icon("alert-triangle"),
    with_close_button=True,
    on_close=State.dismiss_alert,
)
```

Props: `title`, `color`, `variant`, `radius`, `with_close_button`, `icon`, `on_close`.

> [Mantine docs — Alert](https://mantine.dev/core/alert/)

## Notification

```python
mn.notification(
    "Your file has been uploaded",
    title="Success",
    color="green",
    icon=rx.icon("check"),
    with_close_button=True,
    loading=False,
)
```

Props: `title`, `color`, `radius`, `icon`, `with_close_button`, `with_border`,
`loading`, `on_close`.

> [Mantine docs — Notification](https://mantine.dev/core/notification/)

## Progress

Simple:

```python
mn.progress(value=65, color="blue", size="lg", striped=True, animated=True)
```

Compound (multi-section with labels):

```python
mn.progress.root(
    mn.progress.section(
        mn.progress.label("Docs 40%"),
        value=40,
        color="blue",
    ),
    mn.progress.section(
        mn.progress.label("Code 25%"),
        value=25,
        color="teal",
    ),
    mn.progress.section(
        mn.progress.label("Tests 15%"),
        value=15,
        color="orange",
    ),
    size="xl",
)
```

Sub-components: `mn.progress.root`, `mn.progress.section`, `mn.progress.label`.

Props: `value`, `color`, `size`, `radius`, `striped`, `animated`, `transition_duration`, `auto_contrast`.

> [Mantine docs — Progress](https://mantine.dev/core/progress/)

## RingProgress

Circular progress ring with optional center label and multiple sections.

```python
mn.ring_progress(
    sections=[
        {"value": 40, "color": "blue", "tooltip": "Done"},
        {"value": 25, "color": "orange", "tooltip": "In progress"},
    ],
    label=mn.text("65%", ta="center", fw=700),
    size=140,
    thickness=12,
    round_caps=True,
    section_gap=4,
)
```

Props: `sections` (list of `{value, color, tooltip?}`), `size`, `thickness`,
`label`, `root_color`, `round_caps`, `section_gap`, `start_angle`, `transition_duration`.

> [Mantine docs — RingProgress](https://mantine.dev/core/ring-progress/)

## SemiCircleProgress

Half-circle gauge (0–100).

```python
mn.semi_circle_progress(
    value=68,
    size=200,
    thickness=12,
    label=mn.text("68%", fw=600),
    label_position="center",  # "center" | "bottom"
    orientation="up",  # "up" | "down"
    fill_direction="left-to-right",  # "left-to-right" | "right-to-left"
    filled_segment_color="blue",
    empty_segment_color="gray.2",
    transition_duration=500,
)
```

Props: `value`, `size`, `thickness`, `label`, `label_position`, `orientation`,
`fill_direction`, `filled_segment_color`, `empty_segment_color`, `transition_duration`.

> [Mantine docs — SemiCircleProgress](https://mantine.dev/core/semi-circle-progress/)

## Loader

Animated loading indicator (spinner, bars, dots).

```python
mn.loader(size="md", color="blue", type="dots")  # "bars" | "dots" | "oval"
```

Props: `size`, `color`, `type`.

> [Mantine docs — Loader](https://mantine.dev/core/loader/)

## Skeleton

Placeholder content shape while data loads.

```python
mn.skeleton(height=50, radius="md", animate=True)
mn.skeleton(height=8, radius="xl", visible=State.loading)  # inline
mn.skeleton(height=40, circle=True)  # circular
```

Props: `visible`, `height`, `width`, `circle`, `radius`, `animate`.

> [Mantine docs — Skeleton](https://mantine.dev/core/skeleton/)
