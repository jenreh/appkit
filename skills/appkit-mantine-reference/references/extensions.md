# Extensions Reference

Mantine ships additional packages beyond `@mantine/core`. Each requires its own
peer-dependency install and CSS import — `appkit_mantine` handles both
automatically when you use the component.

## Contents

- Carousel (`@mantine/carousel`)
- Dropzone (`@mantine/dropzone`)
- ModalsProvider (`@mantine/modals`)

For calendar / scheduling views (`@mantine/schedule`) see
[references/schedule.md](schedule.md).

## Carousel

Slide show with arrows, indicators, and Embla-powered behaviour. Namespaced:
`mn.carousel(...)` is the root, `mn.carousel.slide(...)` is each slide.

```python
mn.carousel(
    mn.carousel.slide(mn.image(src="/img/1.jpg")),
    mn.carousel.slide(mn.image(src="/img/2.jpg")),
    mn.carousel.slide(mn.image(src="/img/3.jpg")),
    height=300,
    slide_size="50%",
    slide_gap="md",
    orientation="horizontal",  # "horizontal" | "vertical"
    initial_slide=0,
    with_controls=True,
    with_indicators=True,
    with_keyboard_events=True,
    control_size=32,
    controls_offset="md",
    embla_options={"loop": True, "align": "start", "dragFree": False},
    on_slide_change=State.on_slide,  # receives int index
    on_next_slide=State.on_next,
    on_previous_slide=State.on_prev,
)
```

Root props: `height`, `initial_slide`, `orientation`, `slide_size`, `slide_gap`,
`with_controls`, `with_indicators`, `with_keyboard_events`, `control_size`,
`controls_offset`, `include_gap_in_size`, `embla_options` (Embla config dict),
`next_control_icon`, `previous_control_icon`, `on_slide_change`, `on_next_slide`,
`on_previous_slide`.

`carousel.slide` has no special props — just layout/style props.

> [Mantine docs — Carousel](https://mantine.dev/x/carousel/)

## Dropzone

Drag-and-drop file zone. Namespaced state slots render conditionally based on
the current drag state: `mn.dropzone.idle`, `mn.dropzone.accept`,
`mn.dropzone.reject`. Use `mn.dropzone.full_screen` to capture drops anywhere.

```python
mn.dropzone(
    mn.dropzone.idle(mn.text("Drag files here or click")),
    mn.dropzone.accept(mn.text("Drop to upload", c="green")),
    mn.dropzone.reject(mn.text("Files rejected", c="red")),
    accept=["image/png", "image/jpeg", "application/pdf"],
    multiple=True,
    max_files=5,
    max_size=5 * 1024 * 1024,  # bytes
    loading=State.uploading,
    on_drop=State.handle_drop,  # receives list of File objects
    on_reject=State.handle_reject,  # receives list of file rejections
)
```

```python
# Whole-page drop catcher
mn.dropzone.full_screen(
    mn.center(mn.title("Drop files anywhere", order=2)),
    active=True,  # listen for drag events globally
    accept=["image/*"],
    on_drop=State.handle_drop,
)
```

Dropzone props: `accept` (MIME list or react-dropzone Accept dict), `multiple`,
`max_files`, `max_size`, `disabled`, `loading`, `name`, `auto_focus`,
`activate_on_click`, `activate_on_drag`, `activate_on_keyboard`,
`drag_events_bubbling`, `enable_pointer_events`, `prevent_drop_on_document`,
`use_fs_access_api`, `radius`, `accept_color`, `reject_color`, `loader_props`,
`on_drop`, `on_reject`, `on_drop_any` (receives `files, rejections`),
`on_drag_enter`, `on_drag_leave`, `on_file_dialog_open`, `on_file_dialog_cancel`.

`dropzone.full_screen` props: `active`, `within_portal`, `z_index`, `portal_props`
plus all standard Dropzone props.

> [Mantine docs — Dropzone](https://mantine.dev/x/dropzone/)

## ModalsProvider

Enables imperative modal/confirm/dialog management from any state handler.
Wrap your app (or a subtree) once; then call the modals API via `rx.call_script`
or via `appkit_ui` helpers if present.

```python
# In your root layout (typically in app/app.py around app.add_page args)
mn.modals_provider(
    modal_props={"centered": True, "radius": "md"},
    labels={"confirm": "Confirm", "cancel": "Cancel"},
)
```

Props: `modal_props` (default props applied to every imperative modal), `labels`
(default confirm/cancel button text).

> [Mantine docs — Modals manager](https://mantine.dev/x/modals/)

## Notifications (`@mantine/notifications`)

Mount the provider once (page or layout), then return the imperative helpers
from event handlers. They run `notifications.*` in the browser.

```python
mn.notifications_provider(position="top-right", limit=5)


@rx.event
def save(self):
    return mn.notifications.show(
        "Saved",
        title="Done",
        color="teal",
        auto_close=5000,
        with_auto_close_progress=True,
    )
```

Helpers: `show(message, id=, title=, color=, position=, auto_close=,
with_auto_close_progress=, with_close_button=, loading=, ...)`,
`update(id, ...)`, `hide(id)`, `clean()`, `clean_queue()`,
`promise("<js promise expr>", loading={...}, success={...}, error={...})`.
Loading flow: `show(..., id="job", loading=True, auto_close=False)`, later
`update("job", loading=False, color="teal", auto_close=3000)`. Provider props:
`position`, `auto_close`, `limit`, `layout` (`default|stacked`),
`with_auto_close_progress`, `pause_reset_on_hover`, `container_width`.
`promise` takes a JavaScript expression, not a Python value; success/error are
static dicts.

`render_notification` on the provider takes a JS function Var
(`(notification) => ReactNode`) that replaces every notification body.

## Lightbox (`@mantine/lightbox`)

Controlled, or mount `mn.lightbox.provider()` once and open it from handlers.

```python
mn.lightbox(
    opened=State.opened,
    on_close=State.close,
    slides=[{"src": "a.png", "alt": "A", "caption": "A"}],
    current_index=State.index,
    on_index_change=State.set_index,
    with_thumbnails=True,
)

mn.lightbox.provider(with_thumbnails=True)


@rx.event
def open_gallery(self):
    return mn.lightbox_api.open(SLIDES, start_index=2)
```

Slides: images `{src, alt, caption, thumbSrc}` or videos
`{type: "video", src, poster, autoPlay}`. Props: `loop`, `with_zoom`,
`with_thumbnails`, `with_fullscreen`, `with_download`, `with_navigation`,
`with_keyboard_events`, `close_on_click_outside`, `close_on_swipe_down`,
`labels`, `transition_props`, `z_index`, `zoom_max_scale`. Helpers:
`mn.lightbox_api.open/close/next/prev/set_index`.

## ActionBar

```python
mn.action_bar(
    mn.text(State.count.to_string() + " selected", size="sm"),
    mn.action_bar.divider(),
    mn.button("Delete", variant="default", size="compact-sm"),
    mn.action_bar.close_button(),
    opened=State.count > 0,
    on_close=State.clear_selection,
    shadow="md",
)
```

Props: `opened`, `close_on_escape`, `keep_mounted`, `position`, `radius`,
`shadow`, `with_border`, `within_portal`, `transition_props`, `z_index`.

## JsonViewer (`@mantine/code-highlight`)

```python
mn.json_viewer(
    value={"a": 1},
    root_name="data",
    default_expand_depth=2,
    with_copy_button=True,
    with_controls=True,
    with_types=True,
    with_size=True,
    with_border=True,
)
```

Also `with_line_numbers`, `with_chevrons`, `sort_keys`, `all_expanded`,
`highlight_items` (`{serialized_path: "added"|"removed"}`),
`on_value_select(path, value)`, `on_expanded_paths_change(paths)`.
`default_expand_depth` applies on mount only; give the component a `key` to
re-apply it after `value` changes.
