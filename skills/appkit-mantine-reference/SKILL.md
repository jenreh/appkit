---
name: appkit-mantine-reference
description: Complete API reference for appkit_mantine components — inputs, layout, overlays, charts, data display, navigation, menu, table, tree, typography, schedule, and Mantine extensions (carousel, dropzone, code-highlight, modals manager). Use when creating any visible UI with mn.* components. Covers inheritance hierarchy, event handler patterns, colors, anti-patterns, and common pitfalls.
metadata:
  author: jens-rehpoehler
  version: "1.3"
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
— TextInput, NumberInput, PasswordInput, Textarea, TagsInput, Select, MultiSelect, Autocomplete, NativeSelect, TreeSelect, RichSelect, DateInput, DatePickerInput, DateTimePicker, InlineDateTimePicker, MonthPickerInput, YearPickerInput, TimeInput, TimePicker, TimeGrid, MaskedInput, JsonInput, FileInput, PinInput, Rating, Fieldset, Chip/ChipGroup, ColorInput, ColorPicker, AlphaSlider, AngleSlider, HueSlider, Checkbox/CheckboxGroup/CheckboxCard, Radio/RadioGroup/RadioCard, Switch, Slider, RangeSlider, SegmentedControl, Form (input sub-components)

**Layout**: See [references/layout.md](references/layout.md)
— Stack, Group, Flex, Grid, SimpleGrid, Container, Center, Box, Space, Divider, Affix, FocusTrap, AppShell, AspectRatio, Collapse, Marquee, Portal, Scroller, Transition, VisuallyHidden, FloatingWindow, OverflowList

**Overlays**: See [references/overlays.md](references/overlays.md)
— Modal, Drawer, AlertDialog, LoadingOverlay, Overlay, FloatingIndicator, Dialog, Popover

**Data display & feedback**: See [references/data-display.md](references/data-display.md)
— Accordion, Avatar, Badge, Card, Image, BackgroundImage, Paper, Indicator, Timeline, NumberFormatter, RollingNumber, Spoiler, ThemeIcon, ColorSwatch, Kbd, Alert, Notification, Progress, RingProgress, SemiCircleProgress, Loader, Skeleton, Tooltip, HoverCard, Button, ActionIcon, CloseButton, UnstyledButton

**Navigation**: See [references/navigation.md](references/navigation.md)
— Breadcrumbs, Pagination, Stepper, Tabs, NavLink, NavigationProgress, Anchor, Burger, TableOfContents, ScrollArea (autosize/autoscroll/stateful), RichTextEditor, MarkdownPreview

**Menu**: See [references/menu.md](references/menu.md)
— Menu with items, labels, dividers, hover/click triggers, sub-menus

**Table**: See [references/table.md](references/table.md)
— Table with thead/tbody/tr/th/td, sticky header, striped, scroll container, vertical variant

**Tree**: See [references/tree.md](references/tree.md)
— Hierarchical tree view with search, checkboxes, drag-and-drop

**Typography**: See [references/typography.md](references/typography.md)
— Text, Title, Code, List, TypographyStylesProvider

**Typography**: See [references/typography.md](references/typography.md)
— Text, Title, Code, List, Blockquote, Highlight, Mark, TypographyStylesProvider

**Charts**: See [references/charts.md](references/charts.md)
— AreaChart, BarChart, LineChart, CompositeChart, DonutChart, PieChart, RadarChart, RadialBarChart, ScatterChart, BubbleChart, Sparkline, FunnelChart, Heatmap, Treemap, BarsList, SankeyChart

**Date/Time**: See [references/inputs.md](references/inputs.md) (DateInput section)
— DateInput, DatePickerInput, DateTimePicker, InlineDateTimePicker, MonthPickerInput, YearPickerInput, TimeInput, TimePicker, TimeGrid, Calendar, DatePicker, MonthPicker, YearPicker, MiniCalendar

**Schedule** (calendar views): See [references/schedule.md](references/schedule.md)
— Schedule, DayView, WeekView, MonthView, YearView, MobileMonthView

**Extensions**: See [references/extensions.md](references/extensions.md)
— Carousel, CodeHighlight, Dropzone, ModalsProvider

**Theme**: See [references/theme.md](references/theme.md)
— create_theme, mantine_provider (scoped theme override), mermaid_zoom_script

## Decision tree

**Need a form input?** → inputs.md (`mn.text_input`, `mn.number_input`, `mn.select`, `mn.checkbox`, etc.)
**Need a custom input layout (label+description+error)?** → inputs.md (`mn.form.wrapper`, `mn.form.label`, `mn.form.error`)
**Need a date/time picker?** → inputs.md (`mn.date_picker_input`, `mn.time_picker`, `mn.date_time_picker`, `mn.inline_date_time_picker`)
**Need a toggle/selector?** → inputs.md (`mn.segmented_control`, `mn.radio.group`, `mn.checkbox.group`, `mn.chip.group`, `mn.switch`)
**Need a color picker?** → inputs.md (`mn.color_input` with text input, `mn.color_picker` standalone, `mn.hue_slider`, `mn.alpha_slider`)
**Need file upload?** → inputs.md (`mn.file_input` button-style) or extensions.md (`mn.dropzone` drag-and-drop)
**Need a PIN / OTP code entry?** → inputs.md (`mn.pin_input`)
**Need a star rating?** → inputs.md (`mn.rating`)
**Need to group related inputs with a legend?** → inputs.md (`mn.fieldset`)
**Need hierarchical selection?** → inputs.md (`mn.tree_select`)
**Need an angle / direction picker?** → inputs.md (`mn.angle_slider`)
**Need layout?** → layout.md (`mn.stack` vertical, `mn.group` horizontal, `mn.flex`, `mn.grid`)
**Need a full app shell (header / navbar / footer / aside)?** → layout.md (`mn.app_shell`)
**Need fixed aspect ratio container?** → layout.md (`mn.aspect_ratio`)
**Need animated show/hide?** → layout.md (`mn.collapse`, `mn.transition`)
**Need to render in a different DOM node?** → layout.md (`mn.portal`)
**Need scrolling marquee text?** → layout.md (`mn.marquee`)
**Need horizontal scroller with controls?** → layout.md (`mn.scroller`)
**Need a draggable floating panel?** → layout.md (`mn.floating_window`)
**Need to show only first N items + overflow?** → layout.md (`mn.overflow_list`)
**Need a screen-reader-only label?** → layout.md (`mn.visually_hidden`)
**Need a dialog?** → overlays.md (`mn.modal` centered, `mn.drawer` side panel, `mn.alert_dialog` confirmation, `mn.dialog` small floating panel)
**Need a popover anchored to a trigger?** → overlays.md (`mn.popover`)
**Need programmatic modal/confirm management?** → extensions.md (`mn.modals_provider`)
**Need a loading state?** → overlays.md (`mn.loading_overlay`) or data-display.md (`mn.skeleton`, `mn.loader`)
**Need feedback?** → data-display.md (`mn.alert`, `mn.notification`, `mn.progress`, `mn.ring_progress`, `mn.semi_circle_progress`, `mn.skeleton`)
**Need a status label?** → data-display.md (`mn.badge`)
**Need an animated rolling counter?** → data-display.md (`mn.rolling_number`)
**Need expandable/spoiler content?** → data-display.md (`mn.spoiler`)
**Need a colored icon container?** → data-display.md (`mn.theme_icon`)
**Need to display a color sample?** → data-display.md (`mn.color_swatch`)
**Need a keyboard-key display?** → data-display.md (`mn.kbd`)
**Need an X close button?** → data-display.md (`mn.close_button`)
**Need a button with zero styling?** → data-display.md (`mn.unstyled_button`)
**Need a div with a background image?** → data-display.md (`mn.background_image`)
**Need typography?** → typography.md (`mn.text`, `mn.title`, `mn.list_`, `mn.code`)
**Need a styled link?** → navigation.md (`mn.anchor`)
**Need a hamburger menu toggle?** → navigation.md (`mn.burger`)
**Need a page-section navigator?** → navigation.md (`mn.table_of_contents`)
**Need to render highlighted substrings inside text?** → typography.md (`mn.highlight`)
**Need a `<mark>` inline highlight?** → typography.md (`mn.mark`)
**Need a blockquote?** → typography.md (`mn.blockquote`)
**Need a dropdown/context menu?** → menu.md (`mn.menu`)
**Need a custom-rendered select?** → inputs.md (`mn.rich_select` with `mn.rich_select.map(data, renderer=...)`)
**Need chat/streaming scroll?** → navigation.md (`mn.scroll_area.autoscroll`)
**Need tabular data?** → table.md (`mn.table`)
**Need hierarchical data?** → tree.md (`mn.tree`)
**Need charts?** → charts.md (`mn.line_chart`, `mn.bar_chart`, `mn.area_chart`, `mn.radial_bar_chart`, `mn.sankey_chart`, `mn.bars_list`, etc.)
**Need a slideshow / carousel?** → extensions.md (`mn.carousel`)
**Need syntax-highlighted code blocks?** → extensions.md (`mn.code_highlight`)
**Need a calendar/schedule view?** → schedule.md (`mn.schedule`, `mn.schedule.day_view`, `mn.schedule.week_view`, etc.)
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
| `mn.checkbox_group(...)` | `mn.checkbox.group(...)` — namespace sub-component |
| `mn.radio_group(...)` | `mn.radio.group(...)` — namespace sub-component |
| `mn.chip_group(...)` | `mn.chip.group(...)` — namespace sub-component |
| `mn.popover_target(...)` / `mn.popover_dropdown(...)` | `mn.popover.target(...)` / `mn.popover.dropdown(...)` — namespace |
| `mn.dropzone_accept(...)` / `mn.dropzone_idle(...)` | `mn.dropzone.accept(...)` / `mn.dropzone.idle(...)` — namespace |
| `mn.app_shell_header(...)` | `mn.app_shell.header(...)` — namespace |
| `mn.carousel_slide(...)` | `mn.carousel.slide(...)` — namespace |
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
