# Data Display & Feedback Reference

## Contents

- Accordion
- Avatar
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
)
```

Card props: `shadow`, `radius`, `with_border`, `padding`.
Card.Section props: `with_border`, `inherit_padding`.

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

## Progress

Simple:

```python
mn.progress(value=65, color="blue", size="lg", striped=True, animated=True)
```

Compound (multi-section):

```python
mn.progress.root(
    mn.progress.section(value=40, color="blue"),
    mn.progress.section(value=25, color="green"),
    mn.progress.section(value=15, color="yellow"),
    size="xl",
)
```

Props: `value`, `color`, `size`, `radius`, `striped`, `animated`, `transition_duration`.

## Skeleton

```python
mn.skeleton(height=50, radius="md", animate=True)
mn.skeleton(height=8, radius="xl", visible=State.loading)  # inline
mn.skeleton(height=40, circle=True)  # circular
```

Props: `visible`, `height`, `width`, `circle`, `radius`, `animate`.

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

## HoverCard

```python
mn.hover_card(
    mn.hover_card.target(mn.text("Hover me")),
    mn.hover_card.dropdown(
        mn.text("Detailed info appears here"),
    ),
    width=280,
    shadow="md",
    open_delay=200,
)
```

Props: `width`, `shadow`, `open_delay`, `close_delay`, `disabled`.

## Button

```python
mn.button(
    "Click me",
    variant="filled",       # filled, light, subtle, outline, default, gradient, link
    color="blue",
    size="md",
    radius="md",
    loading=State.is_loading,
    disabled=State.is_disabled,
    left_section=rx.icon("download"),
    full_width=True,
    on_click=State.handle_click,
)
```

Props: `variant`, `color`, `size`, `radius`, `gradient`, `disabled`, `loading`,
`loader_props`, `full_width`, `justify`, `left_section`, `right_section`,
`component`, `type`, `on_click`.

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
