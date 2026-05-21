# Typography Reference

## Contents

- Text
- Title
- Code
- List
- TypographyStylesProvider

All inherit from `MantineLayoutComponentBase` — style props (`c`, `fw`, `fz`, `lh`, `ta`, `ff`,
`fs`, `tt`, `td`, `lts`, `w`, `m*`, `p*`) available everywhere.

## Text

General purpose text with typography controls.

```python
mn.text("Hello world", size="lg", fw=700, c="dimmed")
mn.text("Truncated text", line_clamp=2, w=300)
mn.text("Uppercase label", tt="uppercase", fz="xs", fw=600, ls="0.05em")
```

Props: `size` (`xs`/`sm`/`md`/`lg`/`xl`), `fw` (100–900), `c` (color), `ta` (text-align),
`tt` (text-transform), `td` (text-decoration), `fs` (font-style), `ff` (font-family),
`lh` (line-height), `lts` (letter-spacing), `truncate` (`"end"`, `"start"`, `True`),
`line_clamp` (int), `inherit` (use parent font styles), `span` (render as `<span>`),
`gradient`, `variant` (`"gradient"`).

> [Mantine docs — Text](https://mantine.dev/core/text/)

## Title

Semantic heading (`h1`–`h6`) with Mantine theme sizes.

```python
mn.title("Page Title", order=1)
mn.title("Section", order=2, fw=600)
mn.title("Long heading that clips", order=3, line_clamp=1, maw=300)
```

Props: `order` (1–6, default `1`), `size` (override visual size independent of `order`),
`line_clamp`, `fw`, `lh`, `c`, `ta`, `tt`, `text_wrap`
(`"wrap"` | `"nowrap"` | `"balance"` | `"pretty"` | `"stable"`).

> [Mantine docs — Title](https://mantine.dev/core/title/)

## Code

Inline or block monospace code.

```python
mn.code("import appkit_mantine as mn")
mn.code("SELECT * FROM users", color="grape", block=True)
```

Props: `color` (theme color, controls background), `block` (renders as `<pre>` code block).

> [Mantine docs — Code](https://mantine.dev/core/code/)

## List

Ordered and unordered lists. Use `mn.list_` (with underscore) to avoid conflict with Python's
built-in `list`.

```python
mn.list_(
    mn.list_.item("First item"),
    mn.list_.item("Second item"),
    mn.list_.item("Third item"),
    type="ordered",
    spacing="sm",
    size="md",
)
```

Custom icons per item:

```python
mn.list_(
    mn.list_.item("Done", icon=rx.icon("check", color="green")),
    mn.list_.item("Pending", icon=rx.icon("clock", color="orange")),
    mn.list_.item("Error", icon=rx.icon("x", color="red")),
    spacing="xs",
)
```

Props: `type` (`"unordered"` | `"ordered"`), `size`, `spacing`, `center` (align icon/bullet),
`icon` (custom icon for all items), `with_padding`, `list_style_type`.

`mn.list_.item` props: `icon` (per-item override).

> [Mantine docs — List](https://mantine.dev/core/list/)

## TypographyStylesProvider

Applies Mantine's typography CSS styles to arbitrary HTML content (e.g., rendered Markdown or
CMS output). Wraps children so that `<h1>`–`<h6>`, `<p>`, `<a>`, `<code>`, `<ul>`, `<ol>`,
etc. receive Mantine's built-in typographic treatment.

```python
mn.typography_styles_provider(
    rx.html(State.html_content),
    p="md",
)
```

No component-specific props — only inherits layout/style props from
`MantineLayoutComponentBase`.

> [Mantine docs — TypographyStylesProvider](https://mantine.dev/core/typography-styles-provider/)
