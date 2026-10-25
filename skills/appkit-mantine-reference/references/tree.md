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
| `with_checkbox` | `bool` | `False` | Render a checkbox per node (appkit extension) |
| `initial_selected_state` | `list[str]` | `[]` | Values selected on mount |
| `initial_checked_state` | `list[str]` | `[]` | Values checked on mount |
| `initial_expanded_state` | `dict[str, bool]` | `{}` | Expanded nodes on mount, e.g. `{"src": True}` |
| `check_strictly` | `bool` | `False` | Check nodes independently (no parent/child cascade) |
| `with_custom_node` | `bool` | `False` | Use the appkit node renderer (icons per node) |
| `allow_range_selection`, `check_on_space`, `expand_on_space`, `clear_selection_on_outside_click` | `bool` | — | Keyboard / selection behavior |
| `render_node` | JS function | — | Custom node renderer (`rx.Var("(payload) => ...")`) |

## Events

| Event | Payload | When |
|-------|---------|------|
| `on_select` | `list[str]` | Selected node values change |
| `on_check` | `list[str]` | Checked node values change (also once on mount) |
| `on_expand` | `str` | A node is expanded |
| `on_collapse` | `str` | A node is collapsed |

```python
class TreeState(rx.State):
    selected: list[str] = []
    checked: list[str] = []

    @rx.event
    def set_selected(self, values: list[str]) -> None:
        self.selected = values

    @rx.event
    def set_checked(self, values: list[str]) -> None:
        self.checked = values


mn.tree(
    data=data,
    select_on_click=True,
    on_select=TreeState.set_selected,
)
```

The initial state props are read once on mount; the tree is not controlled from
state.

## With search filter

```python
class TreeState(rx.State):
    search: str = ""


mn.stack(
    mn.text_input(
        placeholder="Search...",
        value=TreeState.search,
        on_change=TreeState.set_search,  # explicit @rx.event setter
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
    initial_checked_state=["src/main.py"],
    on_check=TreeState.set_checked,  # list[str] of checked values
    level_offset=20,
)
```

> [Mantine docs — Tree](https://mantine.dev/core/tree/)
