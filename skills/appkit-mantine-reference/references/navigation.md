# Navigation Reference

## Contents

- Breadcrumbs
- Pagination
- Stepper
- Tabs
- NavLink
- NavigationProgress
- ScrollArea
- RichTextEditor (Tiptap)
- MarkdownPreview

## Breadcrumbs

```python
mn.breadcrumbs(
    rx.link("Home", href="/"),
    rx.link("Products", href="/products"),
    rx.text("Details"),
    separator="/",
    separator_margin="sm",
)
```

Props: `separator`, `separator_margin`.

> [Mantine docs — Breadcrumbs](https://mantine.dev/core/breadcrumbs/)

## Pagination

```python
mn.pagination(
    total=20,
    value=State.current_page,
    on_change=State.set_page,
    siblings=1,
    boundaries=1,
    with_edges=True,
    color="blue",
)
```

**on_change receives page number** (int) directly.

Props: `total`, `value`, `default_value`, `siblings`, `boundaries`, `color`,
`radius`, `size`, `with_edges`, `with_controls`, `on_change`.

> [Mantine docs — Pagination](https://mantine.dev/core/pagination/)

## Stepper

```python
mn.stepper(
    mn.stepper.step(label="Step 1", description="Account"),
    mn.stepper.step(label="Step 2", description="Details"),
    mn.stepper.step(label="Step 3", description="Confirm"),
    mn.stepper.completed(rx.text("All done!")),
    active=State.active_step,
    on_step_click=State.set_active_step,
)
```

**on_step_click receives step index** (int) directly.

Stepper props: `active`, `orientation`, `icon_size`, `size`, `color`,
`allow_next_steps_select`, `on_step_click`.

Step props: `label`, `description`, `icon`, `completed_icon`, `loading`,
`allow_step_select`.

> [Mantine docs — Stepper](https://mantine.dev/core/stepper/)

## Tabs

```python
mn.tabs(
    mn.tabs.list(
        mn.tabs.tab("Gallery", value="gallery", left_section=rx.icon("image")),
        mn.tabs.tab("Messages", value="messages", left_section=rx.icon("mail")),
        mn.tabs.tab("Settings", value="settings", left_section=rx.icon("settings")),
        grow=True,
    ),
    mn.tabs.panel(gallery_content(), value="gallery"),
    mn.tabs.panel(messages_content(), value="messages"),
    mn.tabs.panel(settings_content(), value="settings"),
    value=State.active_tab,
    on_change=State.set_active_tab,
    variant="default",
)
```

**on_change receives tab value** (string) directly.

Tabs props: `value`, `default_value`, `orientation`, `color`, `variant`
(`"default"`, `"outline"`, `"pills"`), `keep_mounted`, `inverted`, `on_change`.

Tabs.List props: `grow`, `justify`.
Tabs.Tab props: `value`, `left_section`, `right_section`, `color`, `disabled`.
Tabs.Panel props: `value`, `keep_mounted`.

> [Mantine docs — Tabs](https://mantine.dev/core/tabs/)

## NavLink

```python
mn.nav_link(
    label="Dashboard",
    left_section=rx.icon("dashboard"),
    active=State.current_page == "dashboard",
    on_click=State.navigate_to("dashboard"),
)
```

Props: `label`, `description`, `left_section`, `right_section`, `active`, `disabled`,
`variant` (`"filled"` | `"light"` | `"subtle"` | `"transparent"`), `color`,
`children_offset`, `default_opened`, `opened`, `on_click`.

> [Mantine docs — NavLink](https://mantine.dev/core/nav-link/)

## NavigationProgress

Top-of-page loading bar controlled via JavaScript.

```python
# Add to app root
mn.navigation_progress(color="blue", size=3)


# Control from state
class State(rx.State):
    def start_loading(self):
        return rx.call_script("window.nprogress.start()")

    def stop_loading(self):
        return rx.call_script("window.nprogress.complete()")
```

Props: `color`, `size`, `initial_progress`, `step_interval`, `with_spinner`,
`z_index`.

API: `window.nprogress.start()`, `.stop()`, `.complete()`, `.increment()`,
`.decrement()`, `.set(value)`, `.reset()`.

> [Mantine docs — NavigationProgress](https://mantine.dev/x/navigation-progress/)

## ScrollArea

```python
mn.scroll_area(
    long_content(),
    h=300,
    type="auto",
    scrollbar_size=8,
)
```

Props: `type` (`"auto"`, `"always"`, `"scroll"`, `"hover"`, `"never"`),
`scrollbar_size`, `offset_scrollbars`.

### Variants

| Variant | Usage |
| ------- | ----- |
| `mn.scroll_area(...)` | Basic; requires fixed `h`. |
| `mn.scroll_area.autosize(...)` | **Preferred for lists.** Use `mah` for max-height. |
| `mn.scroll_area.autoscroll(...)` | Auto-scrolls to bottom as content is added; ideal for chat/streaming. |
| `mn.scroll_area.stateful(...)` | Stateful with `persist_key`; used in navbars. |

```python
# Preferred for most lists — scrollable up to 400px
mn.scroll_area.autosize(
    rx.foreach(State.items, item_row),
    mah=400,
    type="hover",
)
```

> [Mantine docs — ScrollArea](https://mantine.dev/core/scroll-area/)

### AutoScroll (chat/streaming)

`mn.scroll_area.autoscroll` automatically scrolls to the bottom when new content is added,
but stops auto-scrolling if the user manually scrolls up.

```python
mn.scroll_area.autoscroll(
    rx.foreach(State.messages, message_row),
    height="400px",  # required — fixed height
    type="auto",
)
```

The scroll snaps back to the bottom on new content only when the user is near the bottom (~50px threshold).

## RichTextEditor (Tiptap)

```python
from appkit_mantine import rich_text_editor, EditorToolbarConfig, ToolbarControlGroup

mn.rich_text_editor(
    content=State.editor_content,
    on_change=State.set_editor_content,
    toolbar=EditorToolbarConfig(
        control_groups=[
            ToolbarControlGroup.BASIC_FORMATTING,
            ToolbarControlGroup.HEADINGS,
            ToolbarControlGroup.LISTS_AND_BLOCKS,
            ToolbarControlGroup.LINKS,
        ]
    ),
    placeholder="Start writing...",
    editable=True,
)
```

Control groups: `BASIC_FORMATTING`, `HEADINGS`, `LISTS_AND_BLOCKS`, `LINKS`,
`ALIGNMENT`, `COLORS`, `HISTORY`, `MEDIA`, `ALL`.

## MarkdownPreview

```python
mn.markdown_preview(
    content=State.markdown_text,
    code_highlight_theme="github-dark",
)
```

Props: `content`, `code_highlight_theme`.

> [Mantine docs — RichTextEditor](https://mantine.dev/x/tiptap/)

## Anchor

Styled hyperlink (Mantine wrapper around `<a>`). Use instead of `rx.link` when you
need Mantine-themed styling, gradients, line-clamp, or hover/underline variants.

```python
mn.anchor(
    "Go to docs",
    href="https://mantine.dev",
    target="_blank",
    underline="hover",  # "always" | "hover" | "not-hover" | "never"
    c="blue",
    size="sm",
    inherit=False,
    line_clamp=1,
)
```

Props: `href`, `target`, `underline`, `size`, `gradient`, `inherit`, `inline`,
`line_clamp`, `on_click`.

> [Mantine docs — Anchor](https://mantine.dev/core/anchor/)

## Burger

Animated hamburger menu toggle — commonly used with `AppShell` navbar collapse.

```python
mn.burger(
    opened=State.nav_opened,
    on_click=State.toggle_nav,
    size="md",
    color="gray.6",
    line_size=2,
    transition_duration=300,
    hidden_from="sm",  # Mantine breakpoint helper
    aria_label="Toggle navigation",
)
```

Props: `opened`, `color`, `size`, `line_size`, `transition_duration`,
`transition_timing_function`, `on_click`.

> [Mantine docs — Burger](https://mantine.dev/core/burger/)

## TableOfContents

Page-section navigator that scroll-spies headings.

```python
mn.table_of_contents(
    initial_data=[
        {"id": "intro", "value": "Introduction", "depth": 1},
        {"id": "setup", "value": "Setup", "depth": 1},
        {"id": "config", "value": "Configuration", "depth": 2},
    ],
    scroll_spy_options={"selector": "h1, h2, h3"},
    color="blue",
    size="sm",
    radius="sm",
    depth_offset=20,
    min_depth_to_offset=2,
    auto_contrast=True,
)
```

Props: `color`, `size`, `radius`, `auto_contrast`, `depth_offset`, `min_depth_to_offset`,
`initial_data`, `scroll_spy_options`.

> [Mantine docs — TableOfContents](https://mantine.dev/core/table-of-contents/)
