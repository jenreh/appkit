# Overlays Reference

## Contents

- Modal
- Drawer

Both inherit from `MantineOverlayComponentBase` which provides shared props:
`opened`, `on_close`, `title`, `size`, `padding`, `radius`, `shadow`, `z_index`,
`close_on_click_outside`, `close_on_escape`, `lock_scroll`, `trap_focus`,
`return_focus`, `with_overlay`, `with_close_button`, `keep_mounted`,
`overlay_props`, `transition_props`, `close_button_props`.

## Modal

```python
mn.modal(
    rx.text("Are you sure?"),
    mn.group(
        mn.button("Cancel", variant="outline", on_click=State.close),
        mn.button("Confirm", on_click=State.confirm),
        justify="flex-end",
    ),
    title="Confirmation",
    opened=State.modal_opened,
    on_close=State.close,
    centered=True,
    size="md",
)
```

Modal-specific props: `centered`, `full_screen`, `x_offset`, `y_offset`, `stack_id`.

### Compound modal

```python
mn.modal.root(
    mn.modal.overlay(background_opacity=0.55, blur=3),
    mn.modal.content(
        mn.modal.header(
            mn.modal.title("Custom Title"),
            mn.modal.close_button(),
        ),
        mn.modal.body("Detailed content"),
    ),
    opened=State.opened,
    on_close=State.close,
)
```

Sub-components: `mn.modal.root`, `mn.modal.overlay`, `mn.modal.content`,
`mn.modal.header`, `mn.modal.title`, `mn.modal.close_button`, `mn.modal.body`.

### State pattern

```python
class ModalState(rx.State):
    opened: bool = False

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.opened = False
```

## Drawer

Side panel overlay.

```python
mn.drawer(
    mn.stack(
        mn.text_input(label="Name"),
        mn.button("Save", on_click=State.save),
    ),
    title="Settings",
    opened=State.drawer_opened,
    on_close=State.close_drawer,
    position="right",
    size="md",
)
```

Drawer-specific props: `position` (`"left"`, `"right"`, `"top"`, `"bottom"`), `offset`.

### Compound drawer

```python
mn.drawer.root(
    mn.drawer.overlay(),
    mn.drawer.content(
        mn.drawer.header(
            mn.drawer.title("Menu"),
            mn.drawer.close_button(),
        ),
        mn.drawer.body("Navigation items"),
    ),
    opened=State.opened,
    on_close=State.close,
    position="left",
)
```

Sub-components: `mn.drawer.root`, `mn.drawer.overlay`, `mn.drawer.content`,
`mn.drawer.header`, `mn.drawer.title`, `mn.drawer.close_button`, `mn.drawer.body`.
