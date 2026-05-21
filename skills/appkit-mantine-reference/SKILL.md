---
name: appkit-mantine-reference
description: Complete API reference for appkit_mantine components — inputs, layout, overlays, charts, data display, navigation, menu, table, tree, typography. Use when creating any visible UI with mn.* components. Covers inheritance hierarchy, event handler patterns, colors, anti-patterns, and common pitfalls.
metadata:
  author: jens-rehpoehler
  version: "1.2"
  license: MIT
---

# Using appkit_mantine Components

## Quick reference

**Import**: `import appkit_mantine as mn`
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
| Select, SegmentedControl | string value or `None` | Direct value, null→`""` |
| MultiSelect, TagsInput, CheckboxGroup | `list[str]` | Direct array |
| RadioGroup | `str` | Direct selected value |
| DateInput | string or `None` | Null converted to `""` |
| Checkbox, Switch | `bool` (checked) | `event.target.checked` extraction |
| Slider | `int \| float` | Direct value |
| RangeSlider | `list[int \| float]` | Direct list `[min, max]` |
| Tabs, Pagination | `str` or `int` | Direct value |
| Menu | `bool` (opened state) | via `on_change` |

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
— TextInput, NumberInput, PasswordInput, Textarea, TagsInput, Select, MultiSelect, Autocomplete, RichSelect, DateInput, DatePickerInput, DateTimePicker, MonthPickerInput, YearPickerInput, TimeInput, TimePicker, TimeGrid, MaskedInput, JsonInput, Checkbox/CheckboxGroup/CheckboxCard, Radio/RadioGroup/RadioCard, Switch, Slider, RangeSlider, SegmentedControl, Form (input sub-components)

**Layout**: See [references/layout.md](references/layout.md)
— Stack, Group, Flex, Grid, SimpleGrid, Container, Center, Box, Space, Divider, Affix, FocusTrap

**Overlays**: See [references/overlays.md](references/overlays.md)
— Modal, Drawer, AlertDialog, LoadingOverlay, Overlay, FloatingIndicator

**Data display & feedback**: See [references/data-display.md](references/data-display.md)
— Accordion, Avatar, Badge, Card, Image, Paper, Indicator, Timeline, NumberFormatter, Alert, Notification, Progress, Skeleton, Tooltip, HoverCard, Button, ActionIcon

**Navigation**: See [references/navigation.md](references/navigation.md)
— Breadcrumbs, Pagination, Stepper, Tabs, NavLink, NavigationProgress, ScrollArea (autosize/autoscroll/stateful), RichTextEditor, MarkdownPreview

**Menu**: See [references/menu.md](references/menu.md)
— Menu with items, labels, dividers, hover/click triggers, sub-menus

**Table**: See [references/table.md](references/table.md)
— Table with thead/tbody/tr/th/td, sticky header, striped, scroll container, vertical variant

**Tree**: See [references/tree.md](references/tree.md)
— Hierarchical tree view with search, checkboxes, drag-and-drop

**Typography**: See [references/typography.md](references/typography.md)
— Text, Title, Code, List, TypographyStylesProvider

**Charts**: See [references/charts.md](references/charts.md)
— AreaChart, BarChart, LineChart, CompositeChart, DonutChart, PieChart, RadarChart, ScatterChart, BubbleChart, Sparkline, FunnelChart, Heatmap, Treemap

**Date/Time**: See [references/inputs.md](references/inputs.md) (DateInput section)
— DateInput, DatePickerInput, DateTimePicker, MonthPickerInput, YearPickerInput, TimeInput, TimePicker, TimeGrid, Calendar, DatePicker, MonthPicker, YearPicker, MiniCalendar

**Theme**: See [references/theme.md](references/theme.md)
— create_theme, mantine_provider (scoped theme override), mermaid_zoom_script

## Decision tree

**Need a form input?** → inputs.md (`mn.text_input`, `mn.number_input`, `mn.select`, `mn.checkbox`, etc.)
**Need a custom input layout (label+description+error)?** → inputs.md (`mn.form.wrapper`, `mn.form.label`, `mn.form.error`)
**Need a date/time picker?** → inputs.md (`mn.date_picker_input`, `mn.time_picker`, `mn.date_time_picker`)
**Need a toggle/selector?** → inputs.md (`mn.segmented_control`, `mn.radio.group`, `mn.checkbox.group`, `mn.switch`)
**Need layout?** → layout.md (`mn.stack` vertical, `mn.group` horizontal, `mn.flex`, `mn.grid`)
**Need a dialog?** → overlays.md (`mn.modal` centered, `mn.drawer` side panel, `mn.alert_dialog` confirmation)
**Need a loading state?** → overlays.md (`mn.loading_overlay`) or data-display.md (`mn.skeleton`)
**Need feedback?** → data-display.md (`mn.alert`, `mn.notification`, `mn.progress`, `mn.skeleton`)
**Need a status label?** → data-display.md (`mn.badge`)
**Need typography?** → typography.md (`mn.text`, `mn.title`, `mn.list_`, `mn.code`, `mn.anchor`)
**Need a dropdown/context menu?** → menu.md (`mn.menu`)
**Need a custom-rendered select?** → inputs.md (`mn.rich_select` with `mn.rich_select.map(data, renderer=...)`)
**Need chat/streaming scroll?** → navigation.md (`mn.scroll_area.autoscroll`)
**Need tabular data?** → table.md (`mn.table`)
**Need hierarchical data?** → tree.md (`mn.tree`)
**Need charts?** → charts.md (`mn.line_chart`, `mn.bar_chart`, `mn.area_chart`, etc.)
**Need rich text?** → navigation.md (`mn.rich_text_editor` Tiptap-based)
**Need to render HTML/Markdown with Mantine typography styles?** → typography.md (`mn.typography_styles_provider`)
**Need to customise the theme?** → theme.md (`mn.create_theme` + `mn.mantine_provider`)
**Rendering Mermaid diagrams?** → theme.md (`mn.mermaid_zoom_script` to enable click-to-zoom)

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

## Colors

Use the Radix color scale: `<name>.<shade>` where shade is 1–12. Higher shade = darker in light mode:

```python
c="blue.6"           # text color
bg="gray.1"          # background color
bd="red.3"           # border color
"color": "teal.5"    # in chart series dict
rx.color("blue", 4)  # programmatic color (e.g. for rx.cond results)
```

Common color names: `blue`, `gray`, `red`, `green`, `teal`, `orange`, `violet`, `yellow`, `pink`, `dark`.
Use `c="dimmed"` for secondary text.

## Anti-Patterns

| Anti-pattern | Correct approach |
|---|---|
| `rx.vstack` / `rx.hstack` for layout | `mn.stack` / `mn.group` |
| `rx.box` as a container | `mn.card` or `mn.paper` |
| `rx.text` / `rx.heading` for typography | `mn.text` / `mn.title` |
| `mn.list(...)` | `mn.list_(...)` — underscore avoids shadowing Python `list` built-in |
| `mn.mark(...)` / `mn.blockquote(...)` / `mn.anchor(...)` | These don't exist — use `rx.el.mark`, `rx.blockquote`, `rx.link` instead |
| `mn.checkbox_group(...)` | `mn.checkbox.group(...)` — namespace sub-component |
| `mn.radio_group(...)` | `mn.radio.group(...)` — namespace sub-component |
| Inline styles as strings `style="..."` | Mantine style props: `c="blue.6"`, `fw="bold"`, `p="md"` |
| `and` / `or` inside `rx.cond(...)` | Use `&` and `\|` operators |
| Bare Python `if` in component functions | `rx.cond(condition, true_comp, false_comp)` |
| Bare Python `for` in component functions | `rx.foreach(State.items, render_fn)` |
| Custom background on `mn.card` via `background_color`/`--card-bg` | `mn.card` ignores these; wrap in `rx.box` with desired `style` |
| `.to_string()` for number display | Use `de_number(value, ...)` from `alloq_commons.components.formatters` |

## ScrollArea variants

See [references/navigation.md](references/navigation.md) for full ScrollArea docs.

| Variant | When to use |
|---|---|
| `mn.scroll_area.autosize(...)` | **Preferred for lists** — grows to `mah`, then scrolls |
| `mn.scroll_area.autoscroll(...)` | Chat/streaming — auto-scrolls to bottom on new content |
| `mn.scroll_area(...)` | Fixed-height scroll container |
| `mn.scroll_area.stateful(...)` | Navbar with `persist_key` |

```python
mn.scroll_area.autosize(
    rx.foreach(State.items, item_row),
    mah=400,
    type="hover",
)
```

## German number and date formatting

**Always use these helpers — never raw values or `.to_string()`.**

### Numbers

```python
from alloq_commons.components.formatters import de_number

de_number(emp.hours_per_week, suffix="h/W", size="xs", c="var(--alloq-text-muted)", fw="400")
# Renders with German separators: 1.234,5 h/W
# Props: suffix, prefix, size, c, fw, decimal_scale
```

### Dates (display)

```python
from alloq_commons.components.formatters import format_date_de, format_date_de_named

format_date_de(date_var)        # → DD.MM.YYYY
format_date_de_named(date_var)  # → DD. Mon YYYY
```

### Date inputs

```python
mn.date_picker_input(
    value=State.selected_date,
    on_change=State.set_date,
    value_format="DD.MM.YYYY",   # Mantine submits in this format too
)

# Parse in state — handles both DD.MM.YYYY and ISO YYYY-MM-DD:
def _parse_date(value: str) -> date | None:
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
```

---

**→ For state management, event handlers, background tasks, form validation, page factory, service registry, repository pattern, database models, and project architecture, use the `reflex-state-and-architecture` skill.**
