# Overlays Reference

## Contents

- Modal
- Drawer
- AlertDialog
- LoadingOverlay
- Overlay
- FloatingIndicator

Modal and Drawer inherit from `MantineOverlayComponentBase` which provides shared props:
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

> [Mantine docs — Modal](https://mantine.dev/core/modal/)

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

> [Mantine docs — Drawer](https://mantine.dev/core/drawer/)

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

## AlertDialog

Confirmation dialog that blocks interaction until the user explicitly confirms or cancels. Prefer over Modal when an action requires explicit acknowledgment.

```python
mn.alert_dialog.root(
    mn.alert_dialog.content(
        mn.title("Delete item?", order=4),
        mn.text("This action cannot be undone.", size="sm", c="dimmed"),
        mn.alert_dialog.footer(
            cancel_label="Cancel",
            action_label="Delete",
            on_cancel=State.close_dialog,
            on_action=State.confirm_delete,
            action_loading=State.deleting,
        ),
    ),
    open=State.dialog_open,
    on_open_change=State.set_dialog_open,
)
```

**`AlertDialog.root` props:** `open`, `default_open`, `on_open_change`, `size`.

**`AlertDialog.content` props:** `centered` (bool, center on screen).

**`AlertDialog.action` props:** `color`, `variant`, `loading`, `close_on_action` (default `True`), `on_action`.

**`AlertDialog.cancel` props:** `variant`, `on_cancel`.

**`AlertDialog.footer` shorthand** (renders cancel + action buttons):
`cancel_label`, `action_label`, `action_loading`, `on_cancel`, `on_action`.

Sub-components: `mn.alert_dialog.root`, `mn.alert_dialog.content`,
`mn.alert_dialog.cancel`, `mn.alert_dialog.action`, `mn.alert_dialog.footer`.

## LoadingOverlay

Full-area loading overlay shown over a relative-positioned parent.

```python
mn.box(
    mn.loading_overlay(
        visible=State.loading,
        label="Loading data...",
        z_index=10,
    ),
    content(),
    pos="relative",
)
```

Props: `visible`, `z_index`, `label`, `loader_props` (dict passed to Loader),
`overlay_props` (dict with `color`, `background_opacity`, `blur`).

> [Mantine docs — LoadingOverlay](https://mantine.dev/core/loading-overlay/)

## Overlay

Low-level semi-transparent backdrop (not a dialog — just the background layer).

```python
mn.box(
    content(),
    mn.overlay(
        color="#000",
        background_opacity=0.5,
        blur=4,
        z_index=5,
    ),
    pos="relative",
)
```

Props: `color`, `background_opacity` (0–1), `blur`, `gradient`, `z_index`.

> [Mantine docs — Overlay](https://mantine.dev/core/overlay/)

## FloatingIndicator

Animated indicator that follows the active item in a tab-bar or segmented control.

```python
mn.floating_indicator(
    target=State.active_ref,
    parent=State.list_ref,
    transition_duration=200,
)
```

Typically used when building custom tab or pill navigation with animated selection highlight.
Props: `target` (ref of active element), `parent` (ref of container), `transition_duration`.

## Dialog

Small floating panel that stays in place (no backdrop, no focus trap). Use for
contextual prompts, cookie banners, in-app announcements. For modals with backdrops
use `mn.modal` instead.

```python
mn.dialog(
    mn.stack(
        mn.text("Subscribe to our newsletter"),
        mn.text_input(label="Email", value=State.email, on_change=State.set_email),
        mn.button("Subscribe", on_click=State.subscribe, size="xs"),
    ),
    opened=State.dialog_opened,
    on_close=State.close_dialog,
    position={"top": 20, "right": 20},
    size="md",
    radius="md",
    with_close_button=True,
    with_border=True,
    transition_props={"transition": "slide-up", "duration": 200},
    z_index=300,
)
```

Props: `opened`, `on_close`, `position` (dict of `top`/`bottom`/`left`/`right`),
`size`, `radius`, `shadow`, `with_close_button`, `with_border`, `keep_mounted`,
`transition_props`, `close_button_props`, `z_index`.

> [Mantine docs — Dialog](https://mantine.dev/core/dialog/)

## Popover

Anchored floating panel. Namespaced into `target` (trigger) and `dropdown` (content).

```python
mn.popover(
    mn.popover.target(mn.button("Toggle popover")),
    mn.popover.dropdown(
        mn.text("Popover content here"),
    ),
    opened=State.pop_opened,
    on_change=State.set_pop_opened,  # receives bool
    position="bottom",  # 12 floating-ui positions
    offset=8,
    with_arrow=True,
    arrow_size=8,
    trap_focus=False,
    close_on_click_outside=True,
    close_on_escape=True,
    shadow="md",
    width="target",  # "target" | number | "auto"
    radius="md",
    transition_props={"transition": "pop", "duration": 150},
    within_portal=True,
)
```

Root props: `opened`, `default_opened`, `position`, `offset`, `width`, `shadow`,
`radius`, `with_arrow`, `arrow_size`, `arrow_radius`, `arrow_offset`, `arrow_position`,
`trap_focus`, `close_on_click_outside`, `close_on_escape`, `clickout_events`,
`return_focus`, `keep_mounted`, `with_roles`, `within_portal`, `portal_props`,
`z_index`, `middlewares`, `transition_props`, `on_change`, `on_open`, `on_close`,
`on_dismiss`, `on_position_change`.

`popover.target` props: forwarded to the trigger; usually a button or component.

`popover.dropdown` props: standard layout/style props.

`mn.popover.context_menu(...)` (Mantine 9.3) replaces `popover.target` to open
the popover at the cursor on right-click. `arrow_position="merge"` (9.3) merges
the arrow into the dropdown edge; the `prevent_position_change_when_visible`
default became `true` in 9.3 (dropdowns stay put once opened).

> [Mantine docs — Popover](https://mantine.dev/core/popover/)
