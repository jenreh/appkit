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

## NavLink

```python
mn.nav_link(
    label="Dashboard",
    left_section=rx.icon("dashboard"),
    active=State.current_page == "dashboard",
    on_click=State.navigate_to("dashboard"),
)
```

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
