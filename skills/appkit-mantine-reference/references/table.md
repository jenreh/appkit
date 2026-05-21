# Table Reference

Data table with compound sub-components for header, body, rows, and cells.

## Basic usage

```python
mn.table(
    mn.table.thead(
        mn.table.tr(
            mn.table.th("Name"),
            mn.table.th("Email"),
            mn.table.th("Role"),
        ),
    ),
    mn.table.tbody(
        mn.table.tr(
            mn.table.td("Alice"),
            mn.table.td("alice@example.com"),
            mn.table.td("Admin"),
        ),
        mn.table.tr(
            mn.table.td("Bob"),
            mn.table.td("bob@example.com"),
            mn.table.td("User"),
        ),
    ),
    striped=True,
    highlight_on_hover=True,
    with_table_border=True,
)
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `striped` | `bool \| str` | `False` | Alternating row color; `True` = odd rows, `"even"` = even rows |
| `highlight_on_hover` | `bool` | `False` | Highlight row under cursor |
| `with_row_borders` | `bool` | `True` | Show horizontal borders between rows |
| `with_column_borders` | `bool` | `False` | Show vertical borders between columns |
| `with_table_border` | `bool` | `False` | Show outer border around the table |
| `sticky_header` | `bool` | `False` | Pin the `<thead>` to the top when scrolling |
| `sticky_header_offset` | `int` | `0` | Offset for sticky header (e.g. navbar height) |
| `horizontal_spacing` | `str \| int` | `"xs"` | Cell horizontal padding |
| `vertical_spacing` | `str \| int` | `"xs"` | Cell vertical padding |
| `caption_side` | `str` | `"bottom"` | `"top"` or `"bottom"` |
| `tabular_nums` | `bool` | `False` | Use tabular-nums font feature |
| `layout` | `str` | — | CSS table-layout; `"fixed"` for equal column widths |
| `variant` | `str` | — | `"vertical"` for key-value layout |

## Sub-components

| Component | Description |
|-----------|-------------|
| `mn.table.thead(*rows)` | Table head section |
| `mn.table.tbody(*rows)` | Table body section |
| `mn.table.tfoot(*rows)` | Table footer section |
| `mn.table.tr(*cells)` | Table row |
| `mn.table.th(content)` | Header cell |
| `mn.table.td(content)` | Data cell |
| `mn.table.caption(text)` | Table caption |
| `mn.table.scroll_container(*content)` | Wraps table for horizontal scroll |

## Dynamic rows with rx.foreach

```python
class TableState(rx.State):
    rows: list[dict] = [
        {"name": "Alice", "role": "Admin"},
        {"name": "Bob", "role": "User"},
    ]


def user_row(row: dict) -> rx.Component:
    return mn.table.tr(
        mn.table.td(row["name"]),
        mn.table.td(row["role"]),
    )


mn.table(
    mn.table.thead(
        mn.table.tr(mn.table.th("Name"), mn.table.th("Role")),
    ),
    mn.table.tbody(
        rx.foreach(TableState.rows, user_row),
    ),
)
```

## Scrollable table

```python
mn.table.scroll_container(
    mn.table(
        mn.table.thead(
            mn.table.tr(
                rx.foreach(headers, lambda h: mn.table.th(h)),
            ),
        ),
        mn.table.tbody(
            rx.foreach(State.rows, row_component),
        ),
    ),
    h=400,
)
```

## Sticky header

```python
mn.table(
    mn.table.thead(
        mn.table.tr(mn.table.th("Col 1"), mn.table.th("Col 2")),
    ),
    mn.table.tbody(rx.foreach(State.rows, row_component)),
    sticky_header=True,
    sticky_header_offset=60,  # accounts for fixed navbar
)
```

## Vertical variant (key-value)

```python
mn.table(
    mn.table.tbody(
        mn.table.tr(mn.table.th("Name", w=160), mn.table.td("Alice")),
        mn.table.tr(mn.table.th("Role"), mn.table.td("Admin")),
        mn.table.tr(mn.table.th("Email"), mn.table.td("alice@example.com")),
    ),
    variant="vertical",
    layout="fixed",
    with_table_border=True,
)
```

> [Mantine docs — Table](https://mantine.dev/core/table/)
