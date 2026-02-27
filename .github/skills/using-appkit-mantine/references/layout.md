# Layout Reference

## Contents
- Stack (vertical)
- Group (horizontal)
- Flex
- Grid and SimpleGrid
- Container, Center, Box
- Space, Divider
- Affix, FocusTrap

All layout components inherit from `MantineLayoutComponentBase`, providing
Mantine style props: `w`, `h`, `m*`, `p*`, `bg`, `c`, `display`, `pos`, `flex`, etc.

## Stack

Vertical flex container with consistent spacing.

```python
mn.stack(
    mn.text("First"),
    mn.text("Second"),
    mn.text("Third"),
    gap="md",           # xs, sm, md, lg, xl, or number
    align="stretch",    # flex align-items
    justify="flex-start",
)
```

Props: `align`, `justify`, `gap`.

## Group

Horizontal flex container.

```python
mn.group(
    mn.button("Cancel", variant="outline"),
    mn.button("Submit", variant="filled"),
    gap="sm",
    justify="flex-end",
    grow=True,          # children take equal space
)
```

Props: `justify`, `align`, `gap`, `grow`, `prevent_grow_overflow`, `wrap`.

## Flex

Generic flex container with full control.

```python
mn.flex(
    mn.box("A"),
    mn.box("B"),
    gap="md",
    direction="row",
    align="center",
    justify="space-between",
    wrap="wrap",
)
```

Props: `gap`, `row_gap`, `column_gap`, `align`, `justify`, `wrap`, `direction`.
All support responsive objects: `direction={"base": "column", "sm": "row"}`.

## Grid

12-column grid system.

```python
mn.grid(
    mn.grid_col(mn.text("Left"), span=4),
    mn.grid_col(mn.text("Center"), span=4),
    mn.grid_col(mn.text("Right"), span=4),
    gutter="md",
)
```

Grid props: `columns` (default 12), `gutter`, `grow`, `justify`, `align`.
Grid.Col props: `span` (number, "auto", "content", or responsive dict), `offset`, `order`.

Responsive span:
```python
mn.grid_col(content, span={"base": 12, "sm": 6, "md": 4})
```

## SimpleGrid

Auto-layout grid with equal columns.

```python
mn.simple_grid(
    card_1, card_2, card_3, card_4,
    cols={"base": 1, "sm": 2, "lg": 4},
    spacing="md",
)
```

Props: `cols` (int or responsive dict), `spacing`, `vertical_spacing`, `type`.

## Container

Centered content container with max-width.

```python
mn.container(
    mn.title("Page Title"),
    mn.text("Content"),
    size="md",     # xs=540, sm=720, md=960, lg=1140, xl=1320
    fluid=False,   # True = no max-width
)
```

Props: `fluid`, `size`.

## Center

Center content horizontally and vertically.

```python
mn.center(
    mn.text("Centered"),
    inline=True,  # inline-flex instead of flex
)
```

## Box

Generic wrapper with Mantine style props.

```python
mn.box(
    mn.text("Content"),
    w="100%",
    p="md",
    bg="gray.1",
    component="section",  # renders as <section>
)
```

Props: `component` (HTML element).

## Space

Empty space between elements.

```python
mn.stack(
    mn.text("Above"),
    mn.space(h=20),     # vertical space
    mn.text("Below"),
)
```

Style via `h` (height) or `w` (width).

## Divider

Visual separator.

```python
mn.divider(
    label="Or",
    label_position="center",
    orientation="horizontal",
    size="sm",
    variant="dashed",
    color="gray",
)
```

Props: `color`, `label`, `label_position`, `orientation`, `size`, `variant`.

## Affix

Fixed position element.

```python
mn.affix(
    mn.button("Scroll to top", on_click=State.scroll_top),
    position={"bottom": 20, "right": 20},
    z_index=100,
)
```

Props: `position` (dict with `top`/`bottom`/`left`/`right`), `within_portal`, `z_index`.

## FocusTrap

Traps focus within its children.

```python
mn.focus_trap(
    mn.stack(mn.text_input(label="Name"), mn.button("Submit")),
    active=True,
)
```

Props: `active`, `ref_prop`.
