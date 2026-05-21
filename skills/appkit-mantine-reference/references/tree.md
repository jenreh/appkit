# Tree Reference

Hierarchical tree view for file systems, nested navigation, or any recursive data.

## Data shape

```python
data = [
    {
        "label": "src",
        "value": "src",
        "children": [
            {"label": "main.py", "value": "src/main.py"},
            {"label": "utils.py", "value": "src/utils.py"},
        ],
    },
    {"label": "README.md", "value": "README.md"},
]
```

Each node: `{"label": str, "value": str (unique), "children": list (optional)}`.

## Basic usage

```python
mn.tree(
    data=data,
    select_on_click=True,
    expand_on_click=True,
    with_lines=True,
    level_offset=20,
)
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `data` | `list[dict]` | — | Tree data; each node needs `label`, `value`; optional `children` |
| `multiple` | `bool` | `False` | Allow selecting multiple nodes |
| `expand_on_click` | `bool` | `True` | Expand/collapse node when clicked |
| `select_on_click` | `bool` | `False` | Select node when clicked |
| `with_lines` | `bool` | `False` | Show connecting lines between nodes |
| `level_offset` | `int` | `25` | Indentation per level in px |
| `allow_drop` | `bool` | `False` | Enable drag-and-drop reordering |
| `with_drag_handle` | `bool` | `False` | Show drag handles on nodes |
| `keep_mounted` | `bool` | `True` | Keep collapsed children in DOM |
| `search` | `str` | — | Filter nodes by label (appkit extension) |
| `with_checkbox` | `bool` | `False` | Show checkboxes on nodes (appkit extension) |

## Controlled selection via State

```python
class TreeState(rx.State):
    selected: list[str] = []

    def on_select(self, values: list[str]):
        self.selected = values

mn.tree(
    data=State.tree_data,
    select_on_click=True,
    multiple=True,
    on_select=TreeState.on_select,
)
```

## With search filter

```python
class TreeState(rx.State):
    search: str = ""

mn.stack(
    mn.text_input(
        placeholder="Search...",
        value=TreeState.search,
        on_change=TreeState.set_search,
    ),
    mn.tree(
        data=tree_data,
        search=TreeState.search,
        expand_on_click=True,
        with_lines=True,
    ),
)
```

## With checkboxes

```python
mn.tree(
    data=file_tree_data,
    with_checkbox=True,
    expand_on_click=False,  # checkbox clicks handle selection
    level_offset=20,
)
```

> [Mantine docs — Tree](https://mantine.dev/core/tree/)
