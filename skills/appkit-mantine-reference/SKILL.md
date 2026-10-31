---
name: appkit-mantine-reference
description: "MUST invoke when generating mn.* based UIs or the user asks how to use, configure, or debug any mn.* or appkit_mantine component. appkit_mantine is NOT in Claude's training data — always use this skill rather than guessing at APIs. Covers building forms, tables, drawers, modals, tooltips, color pickers, date/time pickers, charts, and navigation; looking up correct props; debugging on_change handler types (NumberInput sends float|str, DateInput sends str|\"\"); troubleshooting component quirks like tooltips on disabled elements, overlays not closing, or props having no effect. Targets Mantine 9.7.3 on Reflex 0.10."
metadata:
  author: jens-rehpoehler
  version: "1.7"
  license: MIT
---

# Using appkit_mantine Components

## Quick reference

**Import**: `import appkit_mantine as mn`
**All components use lowercase factory functions**: `mn.button()`, `mn.text_input()`, `mn.modal()`
**Versions**: Mantine **9.7.3** (`appkit_mantine.base.MANTINE_VERSION`) on Reflex **0.10**.
The references describe exactly this API; every prop they list exists.

## Inheritance hierarchy

```
MantineComponentBase          → library, CSS import, MantineProvider injection
  ↓
MantineLayoutComponentBase    → w, h, m*, p*, bg, c, display, pos, flex, etc.
  ↓
MantineInputComponentBase     → label, description, error, success, value, on_change, sections, etc.
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

Reflex 0.10 creates no automatic `set_*` setters, so every `State.set_x` used in
these docs is an explicit `@rx.event` method you write, typed to match the payload
below.

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
@rx.event
def set_price(self, val: float | str) -> None:
    if val == "":
        self.price = 0.0
        return
    with contextlib.suppress(ValueError):
        self.price = float(val)
```

### DateInput handler example

```python
@rx.event
def set_date(self, value: str) -> None:
    self.selected_date = value  # "" when cleared, ISO string otherwise
```

### JavaScript function props

Render props, predicates and formatters (`render_option`, `render_pill`,
`render_event`, `can_drop_event`, `value_formatter`, `render_notification`, ...)
run in the browser. Pass a JS function, never a Python lambda:

```python
mn.tree_select(
    data=State.tree, render_pill=rx.Var("({ node }) => node.label.toUpperCase()")
)
```

Dict props (`*_props`, `styles`, `class_names`, chart `series`) reach React
unchanged: Reflex camelCases keyword props, not dict keys, so write keys as
Mantine names them (`{"startTime": "08:00:00"}`, `styles={"content": {"minHeight": 300}}`).

## Component categories

**Text inputs**: See [references/inputs-text.md](references/inputs-text.md)
— TextInput, NumberInput, PasswordInput, Textarea, MaskedInput, JsonInput, Form (input sub-components)

**Selection inputs**: See [references/inputs-selection.md](references/inputs-selection.md)
— Select, MultiSelect, Autocomplete, NativeSelect, TreeSelect, Cascader, TagsInput, RichSelect, ComboboxPopover

**Toggle inputs**: See [references/inputs-toggle.md](references/inputs-toggle.md)
— Checkbox/CheckboxGroup/CheckboxCard, Radio/RadioGroup/RadioCard, Switch, Chip/ChipGroup, SegmentedControl, Fieldset

**Date & time inputs**: See [references/inputs-datetime.md](references/inputs-datetime.md)
— DateInput, DatePickerInput, DateTimePicker, InlineDateTimePicker, MonthPickerInput, YearPickerInput, TimeInput, TimePicker, TimeGrid, Calendar, DatePicker, MonthPicker, YearPicker, MiniCalendar

**Specialized inputs**: See [references/inputs-specialized.md](references/inputs-specialized.md)
— Slider, RangeSlider, FileInput, PinInput, Rating, ColorInput, ColorPicker, HueSlider, AlphaSlider, AngleSlider

**Layout**: See [references/layout.md](references/layout.md)
— Stack, Group, Flex, Grid, SimpleGrid, Container, Center, Box, Space, Divider, Affix, FocusTrap, AppShell (+ resizable), AspectRatio, Collapse, Marquee, Portal, Scroller, Transition, VisuallyHidden, FloatingWindow, OverflowList, Splitter

**Overlays**: See [references/overlays.md](references/overlays.md)
— Modal, Drawer, AlertDialog, LoadingOverlay, Overlay, FloatingIndicator, Dialog, Popover, Tour

**Data display**: See [references/data-display.md](references/data-display.md)
— Accordion, Avatar, Badge, Card, Image, BackgroundImage, Paper, Indicator, Timeline, NumberFormatter, RollingNumber, Spoiler, ThemeIcon, ColorSwatch, Kbd, Tooltip, HoverCard, Button, ActionIcon, CloseButton, UnstyledButton, DataList, EmptyState

**Feedback & status**: See [references/feedback.md](references/feedback.md)
— Alert, Notification, Progress, RingProgress, SemiCircleProgress, Loader, Skeleton

**Navigation**: See [references/navigation.md](references/navigation.md)
— Breadcrumbs, Pagination, Stepper, Tabs, NavLink, NavigationProgress, Anchor, Burger, TableOfContents, ScrollArea (autosize/autoscroll/stateful), RichTextEditor, MarkdownPreview, Toggle, Toolbar

**Menu**: See [references/menu.md](references/menu.md)
— Menu with items, labels, dividers, hover/click triggers, sub-menus, search/checkbox/radio items, context menu, Menubar

**Table**: See [references/table.md](references/table.md)
— Table with thead/tbody/tr/th/td, sticky header, striped, scroll container, vertical variant

**Tree**: See [references/tree.md](references/tree.md)
— Hierarchical tree view with search, checkboxes, drag-and-drop

**Typography**: See [references/typography.md](references/typography.md)
— Text, Title, Code, List, Blockquote, Highlight, Mark, TypographyStylesProvider

**Charts**: See [references/charts.md](references/charts.md)
— AreaChart, BarChart, LineChart, CompositeChart, DonutChart, PieChart, RadarChart, RadialBarChart, ScatterChart, BubbleChart, Sparkline, FunnelChart, Heatmap, Treemap, BarsList, SankeyChart, SunburstChart, BulletChart, ChartBrush, GaugeChart, WaffleChart, MatrixChart, CandlestickChart, reference areas/dots

**Schedule** (calendar views): See [references/schedule.md](references/schedule.md)
— Schedule, DayView, WeekView, MonthView, YearView, MobileMonthView, ResourcesSchedule, ResourcesDayView, ResourcesWeekView, ResourcesMonthView, AgendaView

**Extensions**: See [references/extensions.md](references/extensions.md)
— Carousel, Dropzone, ModalsProvider, Notifications, Lightbox, ActionBar, JsonViewer

**Maps**: See [references/maps.md](references/maps.md)
— Map, MapControls, MapMarker (+content/popup/tooltip/label), MapPopup, MapRoute, MapArc, MapGeoJSON, MapClusterLayer, MapNavigation, MapDirectionsPanel

**Theme**: See [references/theme.md](references/theme.md)
— create_theme, mantine_provider (scoped theme override), mermaid_zoom_script

## Decision tree

**Need a text / number / password input?** → inputs-text.md (`mn.text_input`, `mn.number_input`, `mn.password_input`, `mn.textarea`)
**Need a custom input layout (label+description+error)?** → inputs-text.md (`mn.form.wrapper`, `mn.form.label`, `mn.form.error`)
**Need a masked or JSON input?** → inputs-text.md (`mn.masked_input`, `mn.json_input`)
**Need a dropdown / combobox?** → inputs-selection.md (`mn.select`, `mn.multi_select`, `mn.autocomplete`, `mn.native_select`)
**Need a combobox dropdown on a plain button (no input)?** → inputs-selection.md (`mn.combobox_popover`)
**Need a tags input?** → inputs-selection.md (`mn.tags_input`)
**Need hierarchical selection?** → inputs-selection.md (`mn.tree_select`, or `mn.cascader` for drill-down columns)
**Need a custom-rendered select?** → inputs-selection.md (`mn.rich_select` with `mn.rich_select.map(data, renderer=...)`)
**Need a toggle/selector?** → inputs-toggle.md (`mn.segmented_control`, `mn.radio.group`, `mn.checkbox.group`, `mn.chip.group`, `mn.switch`)
**Need to group related inputs with a legend?** → inputs-toggle.md (`mn.fieldset`)
**Need a date/time picker?** → inputs-datetime.md (`mn.date_picker_input`, `mn.time_picker`, `mn.date_time_picker`, `mn.inline_date_time_picker`)
**Need a range / numeric slider?** → inputs-specialized.md (`mn.slider`, `mn.range_slider`)
**Need a color picker?** → inputs-specialized.md (`mn.color_input` with text input, `mn.color_picker` standalone, `mn.hue_slider`, `mn.alpha_slider`)
**Need file upload?** → inputs-specialized.md (`mn.file_input` button-style) or extensions.md (`mn.dropzone` drag-and-drop)
**Need an interactive map (markers, routes, GeoJSON, clustering, turn-by-turn directions)?** → maps.md (`mn.map`, `mn.map.marker`, `mn.map.route`, `mn.map.geojson`, `mn.map.cluster`, `mn.map.navigation`)
**Need a PIN / OTP code entry?** → inputs-specialized.md (`mn.pin_input`)
**Need a star rating?** → inputs-specialized.md (`mn.rating`)
**Need an angle / direction picker?** → inputs-specialized.md (`mn.angle_slider`)
**Need layout?** → layout.md (`mn.stack` vertical, `mn.group` horizontal, `mn.flex`, `mn.grid`)
**Need a full app shell (header / navbar / footer / aside)?** → layout.md (`mn.app_shell`)
**Need fixed aspect ratio container?** → layout.md (`mn.aspect_ratio`)
**Need animated show/hide?** → layout.md (`mn.collapse`, `mn.transition`)
**Need to render in a different DOM node?** → layout.md (`mn.portal`)
**Need scrolling marquee text?** → layout.md (`mn.marquee`)
**Need horizontal scroller with controls?** → layout.md (`mn.scroller`)
**Need a draggable floating panel?** → layout.md (`mn.floating_window`)
**Need to show only first N items + overflow?** → layout.md (`mn.overflow_list`)
**Need a resizable split-pane layout?** → layout.md (`mn.splitter`, `mn.splitter.pane`)
**Need a user-resizable navbar/aside in the app shell?** → layout.md (`mn.app_shell.resizable`)
**Need a screen-reader-only label?** → layout.md (`mn.visually_hidden`)
**Need a dialog?** → overlays.md (`mn.modal` centered, `mn.drawer` side panel, `mn.alert_dialog` confirmation, `mn.dialog` small floating panel)
**Need a popover anchored to a trigger?** → overlays.md (`mn.popover`)
**Need a guided onboarding tour?** → overlays.md (`mn.tour`, `mn.tour.step`)
**Need a bottom bar for bulk actions on selected rows?** → extensions.md (`mn.action_bar`)
**Need a full-screen image/video gallery viewer?** → extensions.md (`mn.lightbox`, `mn.lightbox_api`)
**Need programmatic modal/confirm management?** → extensions.md (`mn.modals_provider`)
**Need a loading state?** → overlays.md (`mn.loading_overlay`) or feedback.md (`mn.skeleton`, `mn.loader`)
**Need feedback / status messages?** → feedback.md (`mn.alert`, `mn.notification`, `mn.progress`, `mn.ring_progress`, `mn.semi_circle_progress`, `mn.skeleton`)
**Need toast notifications triggered from event handlers?** → extensions.md (`mn.notifications_provider` + `mn.notifications.show`)
**Need a status label?** → data-display.md (`mn.badge`)
**Need an animated rolling counter?** → data-display.md (`mn.rolling_number`)
**Need expandable/spoiler content?** → data-display.md (`mn.spoiler`)
**Need a colored icon container?** → data-display.md (`mn.theme_icon`)
**Need to display a color sample?** → data-display.md (`mn.color_swatch`)
**Need a keyboard-key display?** → data-display.md (`mn.kbd`)
**Need an X close button?** → data-display.md (`mn.close_button`)
**Need a button with zero styling?** → data-display.md (`mn.unstyled_button`)
**Need a div with a background image?** → data-display.md (`mn.background_image`)
**Need to show label/value pairs (definition list)?** → data-display.md (`mn.data_list`)
**Need a "no data" placeholder with a CTA?** → data-display.md (`mn.empty_state`)
**Need typography?** → typography.md (`mn.text`, `mn.title`, `mn.list_`, `mn.code`)
**Need a styled link?** → navigation.md (`mn.anchor`)
**Need a hamburger menu toggle?** → navigation.md (`mn.burger`)
**Need a toggle button or a formatting toolbar?** → navigation.md (`mn.toggle`, `mn.toolbar`)
**Need a page-section navigator?** → navigation.md (`mn.table_of_contents`)
**Need to render highlighted substrings inside text?** → typography.md (`mn.highlight`)
**Need a `<mark>` inline highlight?** → typography.md (`mn.mark`)
**Need a blockquote?** → typography.md (`mn.blockquote`)
**Need a dropdown/context menu?** → menu.md (`mn.menu`, `mn.menu.context_menu`)
**Need a desktop-style menu bar (File/Edit/View)?** → menu.md (`mn.menubar`)
**Need searchable / checkbox / radio menu items?** → menu.md (`mn.menu.search`, `mn.menu.checkbox_item`, `mn.menu.radio_group`)
**Need chat/streaming scroll?** → navigation.md (`mn.scroll_area.autoscroll`)
**Need tabular data?** → table.md (`mn.table`)
**Need hierarchical data?** → tree.md (`mn.tree`)
**Need charts?** → charts.md (`mn.line_chart`, `mn.bar_chart`, `mn.area_chart`, `mn.radial_bar_chart`, `mn.sankey_chart`, `mn.bars_list`, etc.)
**Need a KPI chart?** → charts.md (`mn.gauge_chart`, `mn.bullet_chart`, `mn.waffle_chart`)
**Need a financial or categorical heatmap chart?** → charts.md (`mn.candlestick_chart`, `mn.matrix_chart`)
**Need a slideshow / carousel?** → extensions.md (`mn.carousel`)
**Need a collapsible JSON tree?** → extensions.md (`mn.json_viewer`)
**Need a calendar/schedule view?** → schedule.md (`mn.schedule`, `mn.schedule.day_view`, `mn.schedule.week_view`, etc.)
**Need a resource scheduler (rooms/people as rows)?** → schedule.md (`mn.resources_schedule`, `mn.resources_day_view`, `mn.resources_week_view`, `mn.resources_month_view`)
**Need an agenda list of events by date?** → schedule.md (`mn.agenda_view`)
**Need rich text?** → navigation.md (`mn.rich_text_editor` Tiptap-based)
**Need to render HTML/Markdown with Mantine typography styles?** → typography.md (`mn.typography_styles_provider`)
**Need to customise the theme?** → theme.md (`mn.create_theme` + `mn.mantine_provider`)
**Rendering Mermaid diagrams?** → theme.md (`mn.mermaid_zoom_script` to enable click-to-zoom)

## Reflex 0.10 notes

appkit requires `reflex>=0.10.1`. State vars are descriptors on the declaring
class, which matters for the state and tests behind `mn.*` UIs:

- No auto setters: write each `set_*` handler yourself (see above).
- Do not pass `State._backend_var` as a prop or child (it is a `Field` now);
  use `.default_value()` or a regular var.
- Do not assign `State.var = x` or `monkeypatch.setattr` state vars in tests;
  use `State.__fields__["x"].set_default(...)`.
- Background tasks must write inherited vars inside `async with self`.
- `backend_vars`, `inherited_vars`, `get_skip_vars()` are gone; use
  `get_fields()`.
- Wrapper authors: `get_event_triggers` is a `@classmethod`; keep new props
  snake_case (Reflex camelCases them) and regenerate stubs with `task pyi`.
- Handlers that return `mn.notifications.*` / `rx.call_script` specs work
  unchanged.

## Critical rules

1. **Use only props the references list.** Reflex 0.10 raises no error for an
   undeclared keyword: it silently turns it into CSS (`mn.text(foo="bar")` renders
   `css: {foo: "bar"}`), which is the usual cause of "this prop has
   no effect". For a Mantine prop the wrapper does not declare, pass it as
   `custom_attrs={"camelCaseName": value}`. Undeclared *event* props do fail loudly
   (`ValueError: ... does not take in an on_change event trigger`).
2. **Never redeclare inherited props** — base classes provide ~40 common props
3. **MantineProvider is auto-injected** — no manual wrapping needed
4. **Use `rx.cond` and `rx.foreach`** — never bare Python `if` or `for` in components
5. **Use `&` and `|`** in `rx.cond`, not `and`/`or`
6. **Controlled vs uncontrolled** — use `value` + `on_change` (controlled) or `default_value` (uncontrolled), not both
7. **Path prefix** — apps served below `frontend_path` (e.g. `/knai`): wrap absolute asset `src` (images, files; not page links) in `public_path("/img/x.png")` (`appkit_commons.public_path`) and every `persist_key` in `app_storage_key("x")` (`appkit_user.authentication.states`). Examples below use bare paths for brevity.

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
    w="100%",  # width
    maw=400,  # max-width
    mt="md",  # margin-top
    p="sm",  # padding
    bg="gray.0",  # background
    c="dark.9",  # color
)
```

Available: `w`, `h`, `miw`, `maw`, `mih`, `mah`, `m`, `my`, `mx`, `mt`, `mb`, `ml`, `mr`, `p`, `py`, `px`, `pt`, `pb`, `pl`, `pr`, `bg`, `c`, `display`, `pos`, `flex`, `opacity`, `fz`, `fw`, `ta`, `td`, `bd`, `hidden_from`, `visible_from`, `light_hidden`, `dark_hidden`.

## Colors

Mantine colors are `<name>.<shade>` with shade **0–9** (0 lightest, 9 darkest); a bare
name uses the theme's `primary_shade` (6 by default):

```python
c="blue.6"  # text color
bg="gray.0"  # background color
bd="1px solid red.3"  # border
"color": "teal.5"  # in chart series dict
c=rx.cond(State.ok, "teal.6", "red.6")  # conditional color: just switch the strings
"var(--mantine-color-blue-4)"  # same color as a CSS value (style dicts, light-dark())
```

Common color names: `blue`, `gray`, `red`, `green`, `teal`, `orange`, `violet`, `yellow`, `pink`, `dark`.
Use `c="dimmed"` for secondary text. Do not mix in `rx.color("blue", 4)`: that is the
Radix 1–12 scale and does not follow the Mantine theme.

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
| `.to_string()` for user-facing numbers in alloq apps | `de_number(value, ...)` from `alloq_commons.components.formatters` |

## ScrollArea variants

See [references/navigation.md](references/navigation.md) for full ScrollArea docs.

| Variant | When to use |
|---|---|
| `mn.scroll_area.autosize(...)` | **Preferred for lists** — grows to `mah`, then scrolls |
| `mn.scroll_area.autoscroll(...)` | Chat/streaming — auto-scrolls to bottom on new content |
| `mn.scroll_area(...)` | Fixed-height scroll container |
| `mn.scroll_area.stateful(...)` | Navbar with `persist_key=app_storage_key("navbar_scroll_area")` |

```python
mn.scroll_area.autosize(
    rx.foreach(State.items, item_row),
    mah=400,
    type="hover",
)
```

## German number and date formatting (alloq apps)

Apps that depend on `alloq_commons` must use these helpers instead of raw
values or `.to_string()`. Plain appkit apps do not have `alloq_commons`; use
`mn.number_formatter` there.

### Numbers

```python
from alloq_commons.components.formatters import de_number

de_number(
    emp.hours_per_week, suffix="h/W", size="xs", c="var(--alloq-text-muted)", fw="400"
)
# Renders with German separators: 1.234,5 h/W
# Props: suffix, prefix, size, c, fw, decimal_scale
```

### Dates (display)

```python
from alloq_commons.components.formatters import format_date_de, format_date_de_named

format_date_de(date_var)  # → DD.MM.YYYY
format_date_de_named(date_var)  # → DD. Mon YYYY
```

### Date inputs

```python
mn.date_picker_input(
    value=State.selected_date,
    on_change=State.set_date,
    value_format="DD.MM.YYYY",  # Mantine submits in this format too
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
