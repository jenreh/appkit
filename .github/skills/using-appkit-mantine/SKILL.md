```skill
---
name: using-appkit-mantine
description: Builds UI with appkit_mantine — a Reflex wrapper library for Mantine v8.3 components. Use when creating pages, forms, layouts, modals, drawers, charts, inputs, buttons, navigation, or any Mantine-based UI in this project. Covers component API, inheritance hierarchy, event handler patterns, and common pitfalls.
metadata:
  author: jens-rehpoehler
  version: "1.0"
---

# Using appkit_mantine Components

## Quick reference

**Import**: `import appkit_mantine as mn`
**Mantine version**: 8.3.14 (`@mantine/core`)
**All components use lowercase factory functions**: `mn.button()`, `mn.text_input()`, `mn.modal()`

## Inheritance hierarchy

```
MantineComponentBase          → library, CSS import, MantineProvider injection
  ↓
MantineLayoutComponentBase    → w, h, m*, p*, bg, c, display, pos, flex, etc.
  ↓
MantineInputComponentBase     → label, description, error, value, on_change, sections, etc.
  ↓
Specific components           → only component-unique props
```

- `MantineOverlayComponentBase` extends `MantineLayoutComponentBase` → Modal, Drawer shared props

## Creating components

Use factory functions, not class constructors:

```python
import appkit_mantine as mn

mn.text_input(label="Name", value=State.name, on_change=State.set_name)
mn.button("Submit", on_click=State.submit, variant="filled")
mn.stack(mn.text("Hello"), mn.text("World"), gap="md")
```

## Event handler patterns

Default `on_change` uses `rx.event.input_event` (event.target.value). Some components override this:

| Component | on_change receives | Pattern |
|---|---|---|
| TextInput, PasswordInput, Textarea | event object | `on_change=State.set_value` (standard) |
| NumberInput | raw number or `""` | Handler must accept `float \| str` |
| Select | string value or `None` | Direct value, null→`""` |
| MultiSelect | `list[str]` | Direct array |
| DateInput | string or `None` | Null converted to `""` |
| Checkbox, Radio, Switch | `bool` (checked) | `event.target.checked` extraction |
| Slider | `int \| float` | Direct value |
| Tabs, Pagination | `str` or `int` | Direct value |

### NumberInput handler example

```python
def set_price(self, val: float | str) -> None:
    if val == "":
        self.price = 0.0
        return
    with contextlib.suppress(ValueError):
        self.price = float(val)
```

### DateInput handler example

```python
def set_date(self, value: str) -> None:
    self.selected_date = value  # "" when cleared, ISO string otherwise
```

## Component categories

**Inputs**: See [references/inputs.md](references/inputs.md)
**Layout**: See [references/layout.md](references/layout.md)
**Overlays**: See [references/overlays.md](references/overlays.md)
**Data display & feedback**: See [references/data-display.md](references/data-display.md)
**Navigation**: See [references/navigation.md](references/navigation.md)
**Charts**: See [references/charts.md](references/charts.md)

## Decision tree

**Need a form input?** → Use `mn.text_input`, `mn.number_input`, `mn.select`, etc.
**Need layout?** → Use `mn.stack` (vertical), `mn.group` (horizontal), `mn.flex`, `mn.grid`
**Need a dialog?** → Use `mn.modal` (centered) or `mn.drawer` (side panel)
**Need feedback?** → Use `mn.alert`, `mn.notification`, `mn.progress`, `mn.skeleton`
**Need charts?** → Use `mn.line_chart`, `mn.bar_chart`, `mn.area_chart`, etc.
**Need rich text?** → Use `mn.rich_text_editor` (Tiptap-based)

## Critical rules

1. **Never redeclare inherited props** — base classes provide ~40 common props
2. **MantineProvider is auto-injected** — no manual wrapping needed
3. **Use `rx.cond` and `rx.foreach`** — never bare Python `if` or `for` in components
4. **Use `&` and `|`** in `rx.cond`, not `and`/`or`
5. **Controlled vs uncontrolled** — use `value` + `on_change` (controlled) or `default_value` (uncontrolled), not both

## Namespace components (compound pattern)

Some components use namespaces for sub-components:

```python
mn.accordion(
    mn.accordion.item(
        mn.accordion.control("Section 1"),
        mn.accordion.panel("Content 1"),
        value="section-1",
    ),
)

mn.tabs(
    mn.tabs.list(
        mn.tabs.tab("Tab 1", value="1"),
        mn.tabs.tab("Tab 2", value="2"),
    ),
    mn.tabs.panel(rx.text("Content 1"), value="1"),
    mn.tabs.panel(rx.text("Content 2"), value="2"),
    value=State.active_tab,
    on_change=State.set_active_tab,
)

mn.modal(
    rx.text("Content"),
    title="My Modal",
    opened=State.opened,
    on_close=State.close_modal,
)
```

## Mantine style props

All layout/input components support Mantine's style system props directly:

```python
mn.text_input(
    label="Email",
    w="100%",       # width
    maw=400,        # max-width
    mt="md",        # margin-top
    p="sm",         # padding
    bg="gray.0",    # background
    c="dark.9",     # color
)
```

Available: `w`, `h`, `miw`, `maw`, `mih`, `mah`, `m`, `my`, `mx`, `mt`, `mb`, `ml`, `mr`, `p`, `py`, `px`, `pt`, `pb`, `pl`, `pr`, `bg`, `c`, `display`, `pos`, `flex`, `opacity`, `fz`, `fw`, `ta`, `td`, `bd`, `hidden_from`, `visible_from`.
```
