import reflex as rx

from appkit_imagecreator.state import ImageGalleryState

# -----------------------------------------------------------------------------
# Config Popup Component (Size & Quality)
# -----------------------------------------------------------------------------


def _size_option(option: dict) -> rx.Component:
    """Render a size option item."""
    return rx.box(
        rx.hstack(
            rx.cond(
                ImageGalleryState.selected_size == option["label"],
                rx.icon("check", size=16, color=rx.color("accent", 9)),
                rx.box(width="16px"),
            ),
            rx.text(option["label"], size="2"),
            spacing="2",
            align="center",
            width="100%",
        ),
        padding="8px 12px",
        cursor="pointer",
        border_radius="4px",
        _hover={"background": rx.color("gray", 3)},
        on_click=ImageGalleryState.set_selected_size(option["label"]),
    )


def image_props_popup() -> rx.Component:
    """Popup for selecting size and quality."""
    return rx.popover.root(
        rx.tooltip(
            rx.popover.trigger(
                rx.button(
                    rx.icon("sliders-horizontal", size=17),
                    cursor="pointer",
                    padding="8px",
                    variant="ghost",
                ),
            ),
            content="Wähle die Größe des Bildes",
        ),
        rx.popover.content(
            rx.vstack(
                rx.vstack(
                    rx.foreach(ImageGalleryState.size_options, _size_option),
                    spacing="1",
                    width="100%",
                ),
                spacing="3",
                min_width="200px",
            ),
            side="top",
            align="center",
        ),
        open=ImageGalleryState.config_popup_open,
        on_open_change=lambda _: ImageGalleryState.toggle_config_popup(),
    )
