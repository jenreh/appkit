# Data Display & Feedback Reference

## Contents

- Accordion
- Avatar
- Badge
- Card
- Image
- Paper
- Indicator
- Timeline
- NumberFormatter
- Alert
- Notification
- Progress
- Skeleton
- Tooltip
- HoverCard
- Button and ActionIcon

## Accordion

```python
mn.accordion(
    mn.accordion.item(
        mn.accordion.control("Section 1"),
        mn.accordion.panel("Content for section 1"),
        value="section-1",
    ),
    mn.accordion.item(
        mn.accordion.control("Section 2"),
        mn.accordion.panel("Content for section 2"),
        value="section-2",
    ),
    multiple=True,
    variant="separated",
)
```

Props: `multiple`, `value`, `default_value`, `transition_duration`,
`chevron_position`, `variant` (`"default"`, `"contained"`, `"filled"`, `"separated"`),
`on_change`.

> [Mantine docs — Accordion](https://mantine.dev/core/accordion/)

## Avatar

```python
mn.avatar(src="/img/photo.jpg", alt="User", size="lg", radius="xl")

# Group
mn.avatar.group(
    mn.avatar(src="/img/1.jpg"),
    mn.avatar(src="/img/2.jpg"),
    mn.avatar(name="John Doe"),  # initials auto-generated
    spacing="sm",
)
```

Props: `src`, `alt`, `radius`, `size`, `color`, `variant`, `name`, `allowed_initials_colors`.

> [Mantine docs — Avatar](https://mantine.dev/core/avatar/)

## Badge

Status indicator, label, or count chip.

```python
mn.badge("New", color="blue", variant="light", size="md", radius="sm")
mn.badge("99+", color="red", variant="filled", circle=True)  # circular badge
mn.badge(
    "Premium",
    variant="gradient",
    gradient={"from": "indigo", "to": "cyan"},
    left_section=rx.icon("star", size=12),
)
```

Variants: `filled`, `light`, `outline`, `dot`, `transparent`, `default`, `white`.

Props: `color`, `variant`, `size`, `radius`, `gradient`, `circle`, `full_width`,
`auto_contrast`, `left_section`, `right_section`.

> [Mantine docs — Badge](https://mantine.dev/core/badge/)

## Card

```python
mn.card(
    mn.card.section(mn.image(src="/img/banner.jpg", h=160), with_border=True),
    mn.text("Card title", fw=500),
    mn.text("Description", size="sm", c="dimmed"),
    shadow="sm",
    padding="lg",
    radius="md",
    with_border=True,
    orientation="vertical",  # "vertical" (default) | "horizontal"
)
```

Card props: `shadow`, `radius`, `with_border`, `padding`, `orientation`.
Card.Section props: `with_border`, `inherit_padding`.

> [Mantine docs — Card](https://mantine.dev/core/card/)

## Image

```python
mn.image(
    src="/img/photo.jpg",
    fit="cover",
    radius="md",
    w=200,
    h=150,
    fallback_src="/img/placeholder.jpg",
)
```

Props: `src`, `fit`, `fallback_src`, `radius`, `w`, `h`.

> [Mantine docs — Image](https://mantine.dev/core/image/)

## Paper

```python
mn.paper(
    mn.text("Elevated content"),
    shadow="md",
    radius="md",
    with_border=True,
    p="xl",
)
```

Props: `shadow`, `radius`, `with_border`.

> [Mantine docs — Paper](https://mantine.dev/core/paper/)

## Indicator

```python
mn.indicator(
    mn.avatar(src="/img/user.jpg"),
    color="green",
    size=12,
    processing=True,  # pulsing animation
)
```

Props: `position`, `offset`, `inline`, `size`, `color`, `with_border`,
`disabled`, `processing`, `label`.

> [Mantine docs — Indicator](https://mantine.dev/core/indicator/)

## Timeline

```python
mn.timeline(
    mn.timeline.item(title="Created", bullet=rx.icon("git-branch")),
    mn.timeline.item(title="In Review", bullet=rx.icon("message-circle")),
    mn.timeline.item(title="Merged", bullet=rx.icon("git-merge")),
    active=1,
    bullet_size=24,
)
```

Timeline props: `active`, `reverse_active`, `line_width`, `bullet_size`, `color`, `align`.
Timeline.Item props: `title`, `bullet`, `bullet_size`, `color`, `line_variant`.

> [Mantine docs — Timeline](https://mantine.dev/core/timeline/)

## NumberFormatter

Display-only formatted numbers (not an input).

```python
mn.number_formatter(
    value=1234567.89,
    prefix="$",
    thousand_separator=",",
    decimal_scale=2,
)
```

Props: `allow_negative`, `decimal_scale`, `decimal_separator`, `fixed_decimal_scale`,
`prefix`, `suffix`, `thousand_separator`, `thousands_group_style`.

> [Mantine docs — NumberFormatter](https://mantine.dev/core/number-formatter/)

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

## Skeleton

```python
mn.skeleton(height=50, radius="md", animate=True)
mn.skeleton(height=8, radius="xl", visible=State.loading)  # inline
mn.skeleton(height=40, circle=True)  # circular
```

Props: `visible`, `height`, `width`, `circle`, `radius`, `animate`.

> [Mantine docs — Skeleton](https://mantine.dev/core/skeleton/)

## Tooltip

```python
mn.tooltip(
    mn.button("Hover me"),
    label="Tooltip text",
    position="top",
    with_arrow=True,
    open_delay=200,
)
```

Props: `label`, `position`, `offset`, `open_delay`, `close_delay`, `color`,
`radius`, `with_arrow`, `multiline`, `opened` (controlled).

Floating tooltip: `mn.tooltip.floating(child, label="Follows cursor")`.

> [Mantine docs — Tooltip](https://mantine.dev/core/tooltip/)

## HoverCard

Reveals a card when hovering over a trigger element.

```python
mn.hover_card(
    mn.hover_card.target(
        mn.avatar(src="/img/user.jpg", radius="xl"),
    ),
    mn.hover_card.dropdown(
        mn.stack(
            mn.group(
                mn.avatar(src="/img/user.jpg"),
                mn.stack(
                    mn.text("Alice Smith", fw=500),
                    mn.text("@alice", size="xs", c="dimmed"),
                    gap=2,
                ),
            ),
            mn.text("Full stack developer at Acme Corp.", size="sm"),
            gap="xs",
        ),
    ),
    width=280,
    shadow="md",
    open_delay=200,
    close_delay=150,
)
```

Sub-components: `mn.hover_card.target(child)`, `mn.hover_card.dropdown(*content)`.

Props: `width`, `shadow`, `open_delay`, `close_delay`, `position`, `disabled`.

> [Mantine docs — HoverCard](https://mantine.dev/core/hover-card/)

## Button

```python
mn.button(
    "Click me",
    variant="filled",  # filled, light, subtle, outline, default, gradient, link
    color="blue",
    size="md",
    radius="md",
    loading=State.is_loading,
    disabled=State.is_disabled,
    data_disabled=True,  # visually disabled but keeps pointer events (for Tooltip wrapping)
    left_section=rx.icon("download"),
    full_width=True,
    on_click=State.handle_click,
)
```

Gradient button:

```python
mn.button(
    "Upgrade",
    variant="gradient",
    gradient={"from": "indigo", "to": "cyan", "deg": 45},
)
```

Props: `variant`, `color`, `size`, `radius`, `gradient`, `disabled`, `data_disabled`,
`loading`, `loader_props`, `full_width`, `justify`, `left_section`, `right_section`,
`component`, `type`, `on_click`.

> `data_disabled=True` vs `disabled=True`: `disabled` blocks pointer events entirely (Tooltip won't show); `data_disabled` keeps them active so a wrapping Tooltip still fires.
>
> [Mantine docs — Button](https://mantine.dev/core/button/)

## ActionIcon

Icon-only button.

```python
mn.action_icon(
    rx.icon("settings"),
    variant="subtle",
    size="lg",
    on_click=State.open_settings,
)
```

Props: same as Button minus `left_section`/`right_section`/`full_width`.
Group: `mn.action_icon.group(icon1, icon2, orientation="horizontal")`.

> [Mantine docs — ActionIcon](https://mantine.dev/core/action-icon/)

## CloseButton

X-icon button for closing modals, dismissing alerts, removing tags, etc.

```python
mn.close_button(
    on_click=State.dismiss,
    size="md",
    radius="xl",
    variant="subtle",
    icon_size=16,
    aria_label="Close",
)
```

Props: `size`, `radius`, `icon`, `icon_size`, `variant`, `color`, `disabled`, plus
`MantineButtonBase` props.

> [Mantine docs — CloseButton](https://mantine.dev/core/close-button/)

## UnstyledButton

Button element with no default styling — use when wrapping arbitrary clickable content.

```python
mn.unstyled_button(
    mn.group(
        mn.avatar(src=State.user.avatar),
        mn.text(State.user.name),
    ),
    on_click=State.open_profile,
)
```

No component-specific props beyond `MantineButtonBase` (href, target, type,
loading, loader_props, disabled, etc.).

> [Mantine docs — UnstyledButton](https://mantine.dev/core/unstyled-button/)

## Loader

Animated loading indicator (spinner, bars, dots).

```python
mn.loader(size="md", color="blue", type="dots")  # "bars" | "dots" | "oval"
```

Props: `size`, `color`, `type`.

> [Mantine docs — Loader](https://mantine.dev/core/loader/)

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

## ThemeIcon

Colored icon container — fixed-size box around an icon.

```python
mn.theme_icon(
    rx.icon("check"),
    size="lg",
    radius="xl",
    color="green",
    variant="filled",  # "filled" | "light" | "outline" | "default" | "gradient" | "white" | "transparent"
    gradient={"from": "teal", "to": "lime", "deg": 105},
)
```

Props: `size`, `radius`, `color`, `variant`, `gradient`, `autocontrast`.

> [Mantine docs — ThemeIcon](https://mantine.dev/core/theme-icon/)

## ColorSwatch

Solid-color circular swatch — for palettes, color pickers, indicators.

```python
mn.color_swatch(color="#fa5252", size=24, radius="xl", with_shadow=True)
```

Props: `color`, `size`, `radius`, `with_shadow`.

> [Mantine docs — ColorSwatch](https://mantine.dev/core/color-swatch/)

## Kbd

Renders a keyboard key (`<kbd>`).

```python
mn.group(
    mn.kbd("⌘"),
    mn.text("+", c="dimmed"),
    mn.kbd("K"),
    gap=4,
)
```

Props: `size`, plus standard layout props.

> [Mantine docs — Kbd](https://mantine.dev/core/kbd/)

## Spoiler

Collapses long content with show-more/show-less toggle.

```python
mn.spoiler(
    rx.text(State.long_text),
    max_height=120,
    show_label="Show more",
    hide_label="Hide",
    initial_state=False,
    expanded=State.expanded,
    on_expanded_change=State.set_expanded,
    transition_duration=200,
)
```

Props: `max_height`, `show_label`, `hide_label`, `initial_state`, `expanded`,
`transition_duration`, `control_ref`, `on_expanded_change` (receives `bool`).

> [Mantine docs — Spoiler](https://mantine.dev/core/spoiler/)

## BackgroundImage

Renders any element with a background image (covers, hero blocks).

```python
mn.background_image(
    mn.center(mn.title("Welcome", c="white"), h="100%"),
    src="/img/hero.jpg",
    h=300,
    radius="md",
)
```

Props: `src`, `radius`.

> [Mantine docs — BackgroundImage](https://mantine.dev/core/background-image/)

## RollingNumber

Animated counter that "rolls" when the value changes.

```python
mn.rolling_number(
    value=State.live_count,
    size="xl",
    fw=700,
    duration=500,
)
```

Props: `value` (number), `duration`, `easing`, plus typography style props.

> Mantine extension component.
