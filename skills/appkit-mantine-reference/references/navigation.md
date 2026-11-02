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
`radius`, `size`, `with_edges`, `with_controls`, `layout`, `on_change`.
`layout="responsive"` uses container queries to drop controls when the parent is
narrow.

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
`allow_next_steps_select`, `icon_position`, `label_position` (`"bottom"`
puts label/description under the icon), `on_step_click`.

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
`variant` (`"filled"` | `"light"` | `"subtle"` | `"transparent"`), `color`, `radius`,
`chevron_position`, `default_opened`, `opened`, `transition_duration`, `on_click`.
Nest `mn.nav_link` children for a collapsible group.

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

Props: `color`, `size`, `initial_progress`, `step_interval`, `with_transition`,
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
`scrollbar_size`, `offset_scrollbars`,
`vertical_scrollbar_position` (`"left"` | `"right"`, pins the
vertical scrollbar to a physical side regardless of text direction; useful
for RTL apps; available on all variants including `autosize` and `stateful`).

### Variants

| Variant | Usage |
| ------- | ----- |
| `mn.scroll_area(...)` | Basic; requires fixed `h`. |
| `mn.scroll_area.autosize(...)` | **Preferred for lists.** Use `mah` for max-height. |
| `mn.scroll_area.autoscroll(...)` | Auto-scrolls to bottom as content is added; ideal for chat/streaming. |
| `mn.scroll_area.stateful(...)` | Stateful with `persist_key` (a localStorage key; use `app_storage_key("...")` so apps on one origin don't share it); used in navbars. |

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
mn.rich_text_editor(
    content=State.editor_content,
    on_update=State.set_editor_content,  # receives the HTML string
    toolbar_config=mn.EditorToolbarConfig(
        control_groups=[
            mn.ToolbarControlGroup.BASIC_FORMATTING.value,
            mn.ToolbarControlGroup.HEADINGS.value,
            ["link", "unlink"],  # or a custom list of control names
        ],
        sticky=True,
    ),
    placeholder="Start writing...",
    editable=True,
    styles={"content": {"minHeight": "300px"}},
)
```

The change event is `on_update`, not `on_change`, and the toolbar goes in
`toolbar_config` (an `EditorToolbarConfig`, not a state Var). Pass group
members with `.value`. Other props: `variant` (`default|subtle`),
`with_typography_styles`, `labels`, `show_toolbar`, `sticky_offset`,
`class_names`, and image upload (`image_upload_url`, `image_upload_field`,
`image_upload_headers`, `on_image_upload_error`). While the editor has focus
it ignores incoming `content` updates, so typing does not reset the cursor.

Control groups: `BASIC_FORMATTING`, `HEADINGS`, `LISTS_AND_BLOCKS`, `LINKS`,
`ALIGNMENT`, `COLORS`, `HISTORY`, `MEDIA`, `UPLOAD`, `TABLE`, `DETAILS`,
`INVISIBLE_CHARACTERS`, `ALL`. Table controls (`tableInsert`,
`tableColumnBefore`, `tableRowAfter`, `tableMergeCells`, ...) are disabled
outside a table; `details` wraps the block in a collapsible section;
`invisibleCharacters` toggles formatting marks.

## MarkdownPreview

Renders Markdown with `@uiw/react-markdown-preview` (not a Mantine component);
follows the Reflex color mode.

```python
mn.markdown_preview(
    source=State.markdown_text,
    enable_mermaid=State.done_streaming,  # render ```mermaid fences as diagrams
    enable_katex=State.done_streaming,  # render $...$ math
    security_level="standard",  # "strict" | "standard" | "none"
)
```

Props: `source`, `security_level` (`"strict"` sanitizes all HTML, `"none"`
renders raw HTML), `enable_mermaid`, `enable_katex`, `disable_copy`,
`remark_plugins`, `rehype_plugins`, `rehype_rewrite`, `components`,
`wrapper_element`, `prefix_cls`, `class_name`. Turn Mermaid/KaTeX on only after
streaming finishes, so half-written blocks are not parsed. For click-to-zoom on
diagrams add `mn.mermaid_zoom_script()` (theme.md).

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

## Toggle and Toolbar

`mn.toggle` is a button with an active state: `active` / `default_active`,
`on_active_change(bool)`, `auto_width`, `auto_contrast`, `variant`, `color`.
Icon-only toggles need `aria_label`.

`mn.toolbar` groups toggles with roving tabindex (one tab stop, arrow keys
move focus): `orientation`, `loop`, `with_border`, `variant`, `size`.

```python
mn.toolbar(
    mn.toolbar.toggle_group(
        mn.toolbar.toggle_item("B", value="bold", aria_label="Bold"),
        mn.toolbar.toggle_item("I", value="italic", aria_label="Italic"),
        type="multiple",
        value=State.formatting,
        on_change=State.set_formatting,
    ),
    mn.toolbar.divider(),
    mn.toolbar.toggle_group(..., type="single", default_value="left"),
)
```

`type="multiple"` gives/accepts `list[str]`; `type="single"` a `str` (the
handler receives `None` when the active item is clicked again, so type it
`str | None`). `mn.toolbar.toggle(active=...)` is the stateless variant;
`mn.toolbar.group` groups without selection state.

### RichTextEditor image upload

Add the `imageUpload` control (`ToolbarControlGroup.UPLOAD`) and optionally
`image_upload_url="/upload"` (multipart POST, field `image_upload_field`,
default `file`; answer JSON `{"url": ...}` or a plain URL),
`image_upload_headers`, `on_image_upload_error(message)`. Pick, drop and paste
all upload. Without a URL images are inlined as data URLs.
