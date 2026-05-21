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
`next_control_icon`, `previous_control_icon`, `next_control_props`,
`previous_control_props`, `on_slide_change`, `on_next_slide`, `on_previous_slide`.

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
