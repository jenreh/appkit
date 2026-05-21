# Inputs — Selection & Dropdowns

## Contents

- TagsInput
- Select
- MultiSelect
- Autocomplete
- NativeSelect
- TreeSelect
- RichSelect

All selection inputs inherit from `MantineInputComponentBase` (`label`, `description`, `error`,
`required`, `value`, `default_value`, `placeholder`, `disabled`, `on_change`, etc.).

## TagsInput

```python
mn.tags_input(
    label="Skills",
    data=["React", "Python", "TypeScript"],
    default_value=["Python"],  # pre-selected tags
    placeholder="Add a skill",
    max_tags=5,
    allow_new=False,  # only allow values from data list
    on_change=State.set_tags,
)
```

**on_change receives `list[str]`** directly.

Props: `data`, `accept_value_on_blur`, `allow_duplicates`, `allow_new`,
`max_tags`, `split_chars`, `clearable`, `on_search_change`, `on_duplicate`, `on_remove`.

> [Mantine docs — TagsInput](https://mantine.dev/core/tags-input/)

## Select

```python
mn.select(
    label="Framework",
    data=["React", "Vue", "Angular"],
    default_value="React",
    searchable=True,
    clearable=True,
    nothing_found_message="No match",
    on_change=State.set_framework,
)
```

**on_change receives string value directly** (or `""` when null/cleared).

Data formats: `list[str]` or `list[dict]` with `value` and `label` keys.

Grouped data:

```python
data = [
    {"group": "Frontend", "items": ["React", "Vue"]},
    {"group": "Backend", "items": ["Django", "FastAPI"]},
]
```

Props: `allow_deselect`, `auto_select_on_blur`, `render_option`,
`select_first_option_on_change`, `with_check_icon`, `check_icon_position`.

> [Mantine docs — Select](https://mantine.dev/core/select/)

## MultiSelect

```python
mn.multi_select(
    label="Technologies",
    data=["React", "Vue", "Angular", "Svelte"],
    default_value=["React"],
    searchable=True,
    clearable=True,
    max_values=3,
    on_change=State.set_selected,
)
```

**on_change receives `list[str]`** directly.

Grouped data:

```python
data = [
    {"group": "Frontend", "items": ["React", "Vue"]},
    {"group": "Backend", "items": ["Django", "FastAPI"]},
]
```

Props: `max_values`, `hide_picked_options`, `with_check_icon`, `check_icon_position`,
`clear_search_on_change`.

> [Mantine docs — MultiSelect](https://mantine.dev/core/multi-select/)

## Autocomplete

```python
mn.autocomplete(
    label="City",
    data=["New York", "London", "Tokyo"],
    placeholder="Start typing...",
    on_change=State.set_city,
)
```

**on_change receives string value directly.** Unlike Select, the user can type any value — data
provides suggestions only. Data must be `list[str]`.

Props: `limit`, `filter`, `render_option`, `dropdown_opened`, `on_dropdown_open`,
`on_dropdown_close`, `on_option_submit`.

> [Mantine docs — Autocomplete](https://mantine.dev/core/autocomplete/)

## NativeSelect

Wraps a native HTML `<select>` — use when you want browser-native dropdown UX or need to
support older browsers. No search, no portal — just a plain select.

```python
mn.native_select(
    label="Country",
    description="Choose your country",
    data=["USA", "Canada", "Mexico"],
    value=State.country,
    on_change=State.set_country,  # receives str
)
```

Props: `data` (list of strings or `{value, label}` dicts), `value`, `default_value`,
`label`, `description`, `error`, `required`, `disabled`, `radius`, `size`,
`left_section`, `right_section`, `with_asterisk`, `on_change` (receives `str`).

> [Mantine docs — NativeSelect](https://mantine.dev/core/native-select/)

## TreeSelect

Hierarchical selection in a dropdown — pick from a tree of values.

```python
mn.tree_select(
    label="Category",
    data=[
        {
            "value": "fruits",
            "label": "Fruits",
            "children": [
                {"value": "apple", "label": "Apple"},
                {"value": "banana", "label": "Banana"},
            ],
        },
    ],
    value=State.category,
    on_change=State.set_category,  # str or list[str] depending on mode
    searchable=True,
    clearable=True,
    expand_on_click=True,
    with_lines=True,
)
```

Props: `data`, `value`, `default_value`, `mode` (e.g. `"multiple"`), `searchable`,
`search_value`, `clearable`, `disabled`, `required`, `label`, `description`, `error`,
`radius`, `size`, `max_dropdown_height`, `max_values`, `nothing_found_message`,
`allow_deselect`, `expand_on_click`, `with_lines`, `expanded_values`,
`default_expanded_values`, `default_expand_all`, `on_change`, `on_clear`,
`on_search_change`, `on_dropdown_open`, `on_dropdown_close`, `on_expanded_change`.

> [Mantine docs — TreeSelect](https://mantine.dev/core/tree-select/)

## RichSelect

Advanced combobox with custom option rendering, creatable options, and multi-select support.
Use when `mn.select` or `mn.multi_select` don't offer enough flexibility.

```python
data = [
    {"value": "react", "label": "React", "description": "UI library", "emoji": "⚛️"},
    {"value": "vue", "label": "Vue", "description": "Progressive framework", "emoji": "💚"},
]


def render_option(row: dict) -> rx.Component:
    return mn.group(
        mn.text(row.get("emoji", ""), w="24px"),
        mn.stack(
            mn.text(row["label"], fw=500),
            mn.text(row.get("description", ""), size="xs", c="dimmed"),
            gap=0,
        ),
        gap="xs",
    )


mn.rich_select(
    mn.rich_select.map(data, renderer=render_option),
    placeholder="Pick a framework",
    searchable=True,
    clearable=True,
    value=State.selected,
    on_change=State.set_selected,
)
```

**on_change receives the selected `str` value directly.**

For multi-select mode, pass `values=State.selected_list` and on_change receives `list[str]`.

Creatable (allow user to add new options):

```python
mn.rich_select(
    mn.rich_select.map(State.options, renderer=render_option),
    creatable=True,
    on_create=State.add_option,  # receives the new value string
    searchable=True,
    placeholder="Select or create...",
    on_change=State.set_value,
)
```

Props: `searchable`, `clearable`, `creatable`, `search_placeholder`, `nothing_found`,
`max_dropdown_height`, `position`, `value`, `values` (multi-select list),
`on_change`, `on_create`, `on_search_change`, `on_clear`, `on_opened_change`.
