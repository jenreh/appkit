# Menu Reference

Dropdown menu with items triggered by click or hover.

## Basic usage

```python
mn.menu(
    mn.menu.target(
        mn.button("Options"),
    ),
    mn.menu.dropdown(
        mn.menu.label("Actions"),
        mn.menu.item("Edit", left_section=rx.icon("pencil"), on_click=State.edit),
        mn.menu.item("Duplicate", left_section=rx.icon("copy")),
        mn.menu.divider(),
        mn.menu.item("Delete", left_section=rx.icon("trash"), color="red", on_click=State.delete),
    ),
    width=200,
    position="bottom-start",
    shadow="md",
)
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `opened` | `bool` | — | Controlled open state |
| `default_opened` | `bool` | `False` | Initial open state (uncontrolled) |
| `on_change` | `EventHandler` | — | Called when open state changes |
| `trigger` | `str` | `"click"` | `"click"`, `"hover"`, `"click-hover"` |
| `open_delay` | `int` | `0` | Delay in ms before opening (hover trigger) |
| `close_delay` | `int` | `100` | Delay in ms before closing (hover trigger) |
| `close_on_item_click` | `bool` | `True` | Close menu when any item is clicked |
| `close_on_escape` | `bool` | `True` | Close when Escape is pressed |
| `close_on_click_outside` | `bool` | `True` | Close when clicking outside |
| `position` | `str` | `"bottom"` | Dropdown position relative to target |
| `width` | `int \| str` | `"target"` | Dropdown width; `"target"` matches trigger width |
| `with_arrow` | `bool` | `False` | Show arrow pointing to target |
| `arrow_size` | `int` | `7` | Arrow size in px |
| `shadow` | `str` | `"md"` | Dropdown shadow |
| `z_index` | `int` | `300` | CSS z-index |
| `keep_mounted` | `bool` | `False` | Keep dropdown in DOM when closed |
| `offset` | `int \| dict` | `5` | Distance between target and dropdown |
| `loop` | `bool` | `True` | Loop keyboard navigation |

## Sub-components

| Component | Key props |
|-----------|-----------|
| `mn.menu.target(child)` | Wraps the trigger element |
| `mn.menu.dropdown(*items)` | Wraps the menu content |
| `mn.menu.item(label)` | Clickable item; `left_section`, `right_section`, `color`, `disabled`, `close_on_click`, `on_click` |
| `mn.menu.label(text)` | Non-clickable section label |
| `mn.menu.divider()` | Horizontal separator |

## Hover trigger

```python
mn.menu(
    mn.menu.target(mn.button("Hover me")),
    mn.menu.dropdown(
        mn.menu.item("Profile"),
        mn.menu.item("Settings"),
    ),
    trigger="hover",
    open_delay=200,
    close_delay=400,
    position="right-start",
)
```

> Note: `trigger="click-hover"` is preferred for accessibility — opens on hover on desktop, click on mobile.

## Controlled state

```python
class MenuState(rx.State):
    opened: bool = False

    def toggle(self):
        self.opened = not self.opened

mn.menu(
    mn.menu.target(mn.button("Menu", on_click=MenuState.toggle)),
    mn.menu.dropdown(mn.menu.item("Item 1"), mn.menu.item("Item 2")),
    opened=MenuState.opened,
    on_change=MenuState.set_opened,
)
```

## Item with icon sections

```python
mn.menu.item(
    "Share",
    left_section=rx.icon("share", size=14),
    right_section=mn.text("⌘S", size="xs", c="dimmed"),
    on_click=State.share,
)
```

## Search, checkbox & radio items (Mantine 9.3)

```python
mn.menu(
    mn.menu.target(mn.button("Options")),
    mn.menu.dropdown(
        mn.menu.search(placeholder="Search…"),          # filters items
        mn.menu.checkbox_item(
            "Enable notifications",
            checked=State.notifications,
            on_change=State.set_notifications,           # receives bool
            close_menu_on_click=False,
        ),
        mn.menu.divider(),
        mn.menu.radio_group(                             # value + on_change (str)
            mn.menu.radio_item("List", value="list"),
            mn.menu.radio_item("Grid", value="grid"),
            value=State.view,
            on_change=State.set_view,
        ),
    ),
    close_on_item_click=False,
)
```

`mn.menu.context_menu(...)` opens the menu at the cursor on right-click.
`mn.menu(align_items_labels=True)` aligns item indicator slots.

## Menubar (Mantine 9.4)

Desktop-application style horizontal menu bar. Each `mn.menubar.menu` holds a
top-level `target` and a `dropdown` of `mn.menu.item` children.

```python
mn.menubar(
    mn.menubar.menu(
        mn.menubar.target("File"),
        mn.menubar.dropdown(
            mn.menu.item("New file"),
            mn.menu.item("Open…"),
            mn.menu.divider(),
            mn.menu.item("Save"),
        ),
    ),
    mn.menubar.menu(
        mn.menubar.target("Edit"),
        mn.menubar.dropdown(mn.menu.item("Undo"), mn.menu.item("Redo")),
    ),
)
```

`menubar` props: `default_open_index`, `open_index`, `on_open_change`, `loop`,
`position`, `trigger` (`"click"|"hover"`).

> [Mantine docs — Menu](https://mantine.dev/core/menu/) ·
> [Menubar](https://mantine.dev/core/menubar/)
