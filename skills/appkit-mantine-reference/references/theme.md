# Theme Reference

## Contents

- create_theme
- Colors
- Color schemes
- Typography
- Default component props
- mantine_provider
- mermaid_zoom_script

---

## create_theme

Builds a Mantine theme override dict from snake_case kwargs. Returns a plain
dict passed to `mn.mantine_provider(theme=...)` or the app-wide theme config.

```python
import appkit_mantine as mn

my_theme = mn.create_theme(
    primary_color="violet",
    primary_shade={"light": 5, "dark": 7},
    default_radius="md",
    font_family="Inter, sans-serif",
    headings={
        "fontFamily": "Inter, sans-serif",
        "fontWeight": "700",
    },
    cursor_type="pointer",
    auto_contrast=True,
)
```

### Full prop reference

| Param | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `primary_color` | `str` | `"blue"` | Default color key for buttons, inputs, focus rings, etc. Must be a key in `colors`. |
| `primary_shade` | `int \| dict` | `6` | Which shade index (0–9) to use; dict form `{"light": N, "dark": N}` for per-scheme shades |
| `colors` | `dict[str, list[str]]` | — | Custom palettes — each must have exactly 10 color values |
| `white` | `str` | `"#fff"` | Base white color |
| `black` | `str` | `"#000"` | Base black color |
| `default_radius` | `str \| int` | `"sm"` | Default border radius (`xs`/`sm`/`md`/`lg`/`xl` or px) |
| `font_family` | `str` | system stack | CSS font-family for body text and most components |
| `font_family_monospace` | `str` | system mono | Font for `Code`, `Kbd` components |
| `font_sizes` | `dict` | — | Override `xs`/`sm`/`md`/`lg`/`xl` font sizes |
| `line_heights` | `dict` | — | Override `xs`/`sm`/`md`/`lg`/`xl` line heights |
| `font_smoothing` | `bool` | `True` | Enable `-webkit-font-smoothing: antialiased` |
| `headings` | `dict` | — | `{fontFamily, fontWeight, sizes: {h1: {fontSize, lineHeight}, ...}}` |
| `spacing` | `dict` | — | Override spacing scale (`xs`/`sm`/`md`/`lg`/`xl`) |
| `radius` | `dict` | — | Override border-radius scale |
| `shadows` | `dict` | — | Override box-shadow scale (`xs` … `xl`) |
| `breakpoints` | `dict` | — | Override responsive breakpoints in em units |
| `auto_contrast` | `bool` | `False` | Auto-flip text color for contrast on colored backgrounds |
| `luminance_threshold` | `float` | `0.3` | Threshold for `auto_contrast` calculation |
| `cursor_type` | `str` | `"default"` | `"pointer"` or `"default"` for interactive elements |
| `focus_ring` | `str` | `"auto"` | Focus ring visibility: `"auto"` \| `"always"` \| `"never"` |
| `focus_class_name` | `str` | — | CSS class applied to focused elements |
| `active_class_name` | `str` | — | CSS class applied to active element states |
| `scale` | `float` | `1` | rem scale multiplier |
| `respect_reduced_motion` | `bool` | `False` | Respect `prefers-reduced-motion` OS setting |
| `default_gradient` | `dict` | — | Default gradient for gradient variants `{from, to, deg}` |
| `variant_color_resolver` | callable | — | Custom function for resolving component variant colors |
| `components` | `dict` | — | Default props / styles per component name (see Default component props) |
| `other` | `dict` | — | Arbitrary custom values accessible on the theme object |

---

## Colors

### Color formats

Mantine accepts any valid CSS color format in `colors` palettes and style props:

- HEX: `"#fff"`, `"#4570ed"`
- RGB / RGBA: `"rgb(255, 255, 255)"`, `"rgba(0, 0, 0, 0.5)"`
- HSL / HSLA: `"hsl(0, 0%, 100%)"`, `"hsla(0, 0%, 100%, 0.5)"`
- OKLCH: `"oklch(96.27% 0.0217 238.66)"`

### Custom color palette

Each palette must define **exactly 10 shades** from lightest (index 0) to darkest (index 9):

```python
my_theme = mn.create_theme(
    primary_color="brand",
    colors={
        "brand": [
            "#f0f4ff",  # 0 — lightest
            "#dce7ff",
            "#b9ccff",
            "#8fabfc",
            "#6389f5",
            "#4570ed",  # 5 — primary
            "#3360d4",
            "#274ea8",
            "#1e3d84",
            "#152b5e",  # 9 — darkest
        ]
    },
)
```

### Virtual colors

Virtual colors render differently in light vs. dark mode. Define them in `colors`
using the `virtual_color()` helper:

```python
my_theme = mn.create_theme(
    colors={
        "primary": mn.virtual_color(
            name="primary",
            light="blue",
            dark="cyan",
        )
    },
    primary_color="primary",
)
```

The `name` key must match the dict key in `colors`.

### Using colors on components

The `color` prop on supported components accepts:

| Form | Example | Effect |
| ---- | ------- | ------ |
| Theme key | `"blue"` | Uses `primary_shade` index |
| Indexed theme color | `"blue.5"` | Forces shade 5 |
| Direct CSS value | `"#1D72FE"` | Passed through as-is |

The `c` style prop sets only CSS `color` (text) — useful for fine-grained contrast overrides.

### primaryShade per color scheme

```python
my_theme = mn.create_theme(
    primary_shade={"light": 6, "dark": 8},
)
```

### variantColorResolver

Customize how component variants (filled, outline, etc.) derive their colors:

```python
my_theme = mn.create_theme(
    variant_color_resolver=my_resolver_fn,  # receives (input) → {background, hover, color, border}
)
```

---

## Color schemes

`MantineProvider` manages light / dark / auto color scheme context. The current
scheme is reflected as `data-mantine-color-scheme` on the `<html>` element.

### Provider-level settings

| Prop | Type | Default | Description |
| ---- | ---- | ------- | ----------- |
| `default_color_scheme` | `str` | `"light"` | Fallback when no stored preference exists: `"light"` \| `"dark"` \| `"auto"` |
| `force_color_scheme` | `str` | — | Lock to `"light"` or `"dark"`, ignoring manager and defaults |
| `color_scheme_manager` | object | localStorage | Custom storage implementation for persisting the user's preference |

### Conditional rendering by scheme

Components expose `light_hidden` / `dark_hidden` boolean props:

```python
mn.text("Only in light mode", light_hidden=False, dark_hidden=True)
mn.text("Only in dark mode", light_hidden=True, dark_hidden=False)
```

---

## Typography

Three theme keys control fonts; all others fall back to `font_family`:

| Key | Applies to |
| --- | ---------- |
| `font_family` | Most components (Button, Input, Text, …) |
| `font_family_monospace` | `Code`, `Kbd` |
| `headings.fontFamily` | h1–h6; falls back to `font_family` if unset |

### Full typography example

```python
my_theme = mn.create_theme(
    font_family="Inter, sans-serif",
    font_family_monospace="JetBrains Mono, monospace",
    font_sizes={
        "xs": "0.75rem",
        "sm": "0.875rem",
        "md": "1rem",
        "lg": "1.125rem",
        "xl": "1.25rem",
    },
    line_heights={
        "xs": "1.4",
        "sm": "1.45",
        "md": "1.55",
        "lg": "1.6",
        "xl": "1.65",
    },
    headings={
        "fontFamily": "Inter, sans-serif",
        "fontWeight": "700",
        "sizes": {
            "h1": {"fontSize": "2.25rem", "lineHeight": "1.3"},
            "h2": {"fontSize": "1.875rem", "lineHeight": "1.35"},
            "h3": {"fontSize": "1.5rem", "lineHeight": "1.4"},
        },
    },
)
```

---

## Default component props

Set default props for any Mantine component via `theme.components`. These apply
app-wide unless overridden at the call site.

```python
my_theme = mn.create_theme(
    components={
        "Button": {
            "defaultProps": {
                "radius": "xl",
                "size": "md",
            }
        },
        "TextInput": {
            "defaultProps": {
                "size": "sm",
            }
        },
        # Compound components drop the dot: Menu.Item → MenuItem
        "MenuItem": {
            "defaultProps": {
                "color": "blue",
            }
        },
    }
)
```

Priority order (highest → lowest):

1. Props passed directly to the component
2. `theme.components[name].defaultProps`
3. `withProps()` presets
4. `useProps()` built-in defaults

### Scoped defaults with mantine_provider

Wrap a subtree with `mn.mantine_provider` to apply different defaults to only
that section without affecting the rest of the app:

```python
SECTION_THEME = mn.create_theme(
    components={
        "Button": {"defaultProps": {"size": "xs"}},
    }
)


def compact_section() -> rx.Component:
    return mn.mantine_provider(
        content(),
        theme=SECTION_THEME,
    )
```

---

## mantine_provider

Wraps a subtree in a scoped Mantine theme. Use when a page or section needs a
different theme than the app default.

```python
PAGE_THEME = mn.create_theme(
    primary_color="teal",
    default_radius="xl",
)


def themed_page() -> rx.Component:
    return mn.mantine_provider(
        page_content(),
        theme=PAGE_THEME,
    )
```

> `MantineProvider` is auto-injected app-wide. Only use `mn.mantine_provider`
> explicitly when overriding the theme for a specific subtree.

### Props

| Prop | Type | Default | Description |
| ---- | ---- | ------- | ----------- |
| `theme` | `dict` | — | Theme overrides from `mn.create_theme(...)` |
| `default_color_scheme` | `str` | `"light"` | Initial scheme: `"light"` \| `"dark"` \| `"auto"` |
| `force_color_scheme` | `str` | — | Lock to `"light"` or `"dark"` |
| `color_scheme_manager` | object | localStorage | Custom color scheme storage |
| `with_css_variables` | `bool` | `True` | Inject CSS custom properties |
| `css_variables_selector` | `str` | `":root"` | Selector where CSS vars are attached |
| `deduplicate_css_variables` | `bool` | `True` | Skip redundant CSS vars that match defaults |
| `css_variables_resolver` | callable | — | Custom function returning extra CSS variable styles |
| `class_names_prefix` | `str` | `"mantine"` | Prefix for static class names like `mantine-Button-root` |
| `with_static_classes` | `bool` | `True` | Enable `mantine-*` static classes on components |
| `with_global_classes` | `bool` | `True` | Global utility classes; required for `hidden_from` / `visible_from` |
| `env` | `str` | — | Set to `"test"` to disable transitions and portals in tests |

---

## mermaid_zoom_script

One-time script that enables click-to-zoom on Mermaid diagrams rendered inside
`mn.markdown_preview`. Add once at the root of any page that renders Mermaid.

```python
@navbar_layout(route="/docs", ...)
def docs_page() -> rx.Component:
    return mn.container(
        mn.mermaid_zoom_script(),
        mn.markdown_preview(content=State.markdown_content),
    )
```

No props. Must be present in the component tree of the page where Mermaid diagrams appear.
