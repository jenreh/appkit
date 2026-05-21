# Layout Reference

## Contents

- Stack (vertical)
- Group (horizontal)
- Flex
- Grid and SimpleGrid
- Container, Center, Box
- Space, Divider
- Affix, FocusTrap

All layout components inherit from `MantineLayoutComponentBase`, providing
Mantine style props: `w`, `h`, `m*`, `p*`, `bg`, `c`, `display`, `pos`, `flex`, etc.

## Stack

Vertical flex container with consistent spacing.

```python
mn.stack(
    mn.text("First"),
    mn.text("Second"),
    mn.text("Third"),
    gap="md",  # xs, sm, md, lg, xl, or number
    align="stretch",  # flex align-items
    justify="flex-start",
)
```

Props: `align`, `justify`, `gap`.

> [Mantine docs — Stack](https://mantine.dev/core/stack/)

## Group

Horizontal flex container.

```python
mn.group(
    mn.button("Cancel", variant="outline"),
    mn.button("Submit", variant="filled"),
    gap="sm",
    justify="flex-end",
    grow=True,  # children take equal space
)
```

Props: `justify`, `align`, `gap`, `grow`, `prevent_grow_overflow`, `wrap`.

> [Mantine docs — Group](https://mantine.dev/core/group/)

## Flex

Generic flex container with full control.

```python
mn.flex(
    mn.box("A"),
    mn.box("B"),
    gap="md",
    direction="row",
    align="center",
    justify="space-between",
    wrap="wrap",
)
```

Props: `gap`, `row_gap`, `column_gap`, `align`, `justify`, `wrap`, `direction`.
All support responsive objects: `direction={"base": "column", "sm": "row"}`.

> [Mantine docs — Flex](https://mantine.dev/core/flex/)

## Grid

12-column grid system.

```python
mn.grid(
    mn.grid_col(mn.text("Left"), span=4),
    mn.grid_col(mn.text("Center"), span=4),
    mn.grid_col(mn.text("Right"), span=4),
    gutter="md",
)
```

Grid props: `columns` (default 12), `gutter`, `grow`, `justify`, `align`.
Grid.Col props: `span` (number, "auto", "content", or responsive dict), `offset`, `order`.

Responsive span:

```python
mn.grid_col(content, span={"base": 12, "sm": 6, "md": 4})
```

> [Mantine docs — Grid](https://mantine.dev/core/grid/)

## SimpleGrid

Auto-layout grid with equal columns.

```python
mn.simple_grid(
    card_1,
    card_2,
    card_3,
    card_4,
    cols={"base": 1, "sm": 2, "lg": 4},
    spacing="md",
)
```

Props: `cols` (int or responsive dict), `spacing`, `vertical_spacing`, `type`.

> [Mantine docs — SimpleGrid](https://mantine.dev/core/simple-grid/)

## Container

Centered content container with max-width.

```python
mn.container(
    mn.title("Page Title"),
    mn.text("Content"),
    size="md",  # xs=540, sm=720, md=960, lg=1140, xl=1320
    fluid=False,  # True = no max-width
)
```

Props: `fluid`, `size`.

> [Mantine docs — Container](https://mantine.dev/core/container/)

## Center

Center content horizontally and vertically.

```python
mn.center(
    mn.text("Centered"),
    inline=True,  # inline-flex instead of flex
)
```

> [Mantine docs — Center](https://mantine.dev/core/center/)

## Box

Generic wrapper with Mantine style props.

```python
mn.box(
    mn.text("Content"),
    w="100%",
    p="md",
    bg="gray.1",
    component="section",  # renders as <section>
)
```

Props: `component` (HTML element).

> [Mantine docs — Box](https://mantine.dev/core/box/)

## Space

Empty space between elements.

```python
mn.stack(
    mn.text("Above"),
    mn.space(h=20),  # vertical space
    mn.text("Below"),
)
```

Style via `h` (height) or `w` (width).

> [Mantine docs — Space](https://mantine.dev/core/space/)

## Divider

Visual separator.

```python
mn.divider(
    label="Or",
    label_position="center",
    orientation="horizontal",
    size="sm",
    variant="dashed",
    color="gray",
)
```

Props: `color`, `label`, `label_position`, `orientation`, `size`, `variant`.

> [Mantine docs — Divider](https://mantine.dev/core/divider/)

## Affix

Fixed position element.

```python
mn.affix(
    mn.button("Scroll to top", on_click=State.scroll_top),
    position={"bottom": 20, "right": 20},
    z_index=100,
)
```

Props: `position` (dict with `top`/`bottom`/`left`/`right`), `within_portal`, `z_index`.

> [Mantine docs — Affix](https://mantine.dev/core/affix/)

## FocusTrap

Traps focus within its children (useful for modals and drawers rendered manually).

```python
mn.focus_trap(
    mn.stack(mn.text_input(label="Name"), mn.button("Submit")),
    active=True,
)
```

Props: `active`, `ref_prop`.

> [Mantine docs — FocusTrap](https://mantine.dev/core/focus-trap/)

## AppShell

Full application layout — header, navbar, aside, footer, main. Sub-components are
namespaced: `mn.app_shell.header`, `.navbar`, `.aside`, `.footer`, `.main`, `.section`.

```python
mn.app_shell(
    mn.app_shell.header(mn.group(mn.title("My App", order=3))),
    mn.app_shell.navbar(mn.stack(mn.nav_link(label="Home"))),
    mn.app_shell.aside(mn.text("Sidebar")),
    mn.app_shell.footer(mn.text("© 2025")),
    mn.app_shell.main(rx.outlet()),
    header={"height": 60, "collapsed": {"mobile": False}},
    navbar={"width": 250, "breakpoint": "sm", "collapsed": {"mobile": True}},
    aside={
        "width": 300,
        "breakpoint": "md",
        "collapsed": {"mobile": True, "desktop": False},
    },
    footer={"height": 40},
    padding="md",
    layout="default",  # "default" | "alt"
    disabled=False,
    z_index=100,
    transition_duration=200,
)
```

Root props: `header`, `navbar`, `aside`, `footer` (each a dict with `height`/`width`,
`breakpoint`, `collapsed`, `offset`), `padding`, `layout`, `disabled`, `with_border`,
`offset_scrollbars`, `transition_duration`, `transition_timing_function`, `z_index`.

Sub-component props (`header`, `navbar`, `aside`, `footer`, `main`):
`with_border`, `z_index`, `h`, `w`. `section` takes `grow` and standard layout props.

> [Mantine docs — AppShell](https://mantine.dev/core/app-shell/)

## AspectRatio

Locks children to a fixed width/height ratio.

```python
mn.aspect_ratio(
    rx.html(
        '<iframe src="https://www.youtube.com/embed/abc" allowfullscreen></iframe>'
    ),
    ratio=16 / 9,
    maw=600,
)
```

Props: `ratio` (number, e.g. `16/9` or `1`).

> [Mantine docs — AspectRatio](https://mantine.dev/core/aspect-ratio/)

## Collapse

Animates children show/hide via height/opacity.

```python
mn.collapse(
    mn.text("Hidden until opened"),
    in_=State.expanded,  # `in` is reserved in Python
    transition_duration=200,
    transition_timing_function="ease",
    animate_opacity=True,
)
```

Props: `in_` (alias of `in`), `transition_duration`, `transition_timing_function`,
`animate_opacity`, `on_transition_end`.

> [Mantine docs — Collapse](https://mantine.dev/core/collapse/)

## Portal

Renders children into a different DOM node (default: `document.body`). Use for popouts
that must escape `overflow: hidden` ancestors.

```python
mn.portal(
    mn.text("Rendered at document.body"),
    target="#custom-portal-root",  # CSS selector or HTMLElement
    reuse_target_node=True,
)
```

Props: `target`, `reuse_target_node`.

> [Mantine docs — Portal](https://mantine.dev/core/portal/)

## Marquee

Endless horizontal/vertical scrolling content (logos, tickers).

```python
mn.marquee(
    mn.group(
        mn.image(src="/img/logo1.png", h=40),
        mn.image(src="/img/logo2.png", h=40),
        mn.image(src="/img/logo3.png", h=40),
    ),
    speed=40,
    gap="xl",
    direction="left",  # "left" | "right" | "up" | "down"
    pause_on_hover=True,
    fade=True,
    fade_color="white",
)
```

Props: `speed`, `gap`, `direction`, `pause_on_hover`, `fade`, `fade_color`,
`fade_width`, `repeat`, `vertical`.

> [Mantine docs — Marquee](https://mantine.dev/x/marquee/)

## Scroller

Horizontal scroll container with optional next/prev controls.

```python
mn.scroller(
    mn.group(*[mn.card("Item " + str(i), maw=200) for i in range(20)]),
    with_controls=True,
    control_size="lg",
    scroll_by="page",  # "page" | "item" | number
    snap=True,
)
```

Props: `with_controls`, `control_size`, `controls_offset`, `scroll_by`, `snap`,
`previous_control_icon`, `next_control_icon`, `previous_control_props`, `next_control_props`.

> [Mantine docs — Scroller](https://mantine.dev/x/scroller/)

## Transition

Wrapper that animates children mount/unmount.

```python
mn.transition(
    mounted=State.show_panel,
    transition="slide-up",  # "fade", "scale", "slide-up/down/left/right", "pop", "rotate-*"
    duration=200,
    timing_function="ease",
    exit_duration=200,
    keep_mounted=False,
)
```

Props: `mounted`, `transition`, `duration`, `exit_duration`, `timing_function`,
`exit_timing_function`, `enter_delay`, `exit_delay`, `keep_mounted`, `on_entered`,
`on_exited`.

> [Mantine docs — Transition](https://mantine.dev/core/transition/)

## VisuallyHidden

Content visible to screen readers only.

```python
mn.visually_hidden("Loading, please wait")
```

Inherits standard layout/style props. No component-specific props.

> [Mantine docs — VisuallyHidden](https://mantine.dev/core/visually-hidden/)

## FloatingWindow

Draggable / resizable floating panel.

```python
mn.floating_window(
    mn.text("Drag my title bar"),
    title="Properties",
    opened=State.fw_opened,
    on_close=State.close_fw,
    initial_position={"x": 100, "y": 100},
    initial_size={"width": 320, "height": 240},
    resizable=True,
    draggable=True,
    z_index=200,
)
```

Props: `opened`, `on_close`, `title`, `initial_position`, `initial_size`,
`resizable`, `draggable`, `min_width`, `min_height`, `max_width`, `max_height`,
`z_index`, `with_close_button`, `header_props`.

> Mantine extension — see component source for full prop list.

## OverflowList

Renders only items that fit; remaining items appear in an overflow indicator
(e.g. "+3 more").

```python
mn.overflow_list(
    items=State.tags,  # list of dicts
    render_item=lambda item: mn.badge(item.label),
    render_overflow=lambda n: mn.badge(f"+{n}"),
    gap="xs",
    item_min_width=60,
)
```

Props: `items`, `render_item`, `render_overflow`, `gap`, `item_min_width`,
`max_visible`, `align`.

> Mantine extension — typically used for tag rows, breadcrumbs, action toolbars.
