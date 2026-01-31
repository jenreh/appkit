import reflex as rx

from appkit_imagecreator.state import ImageGalleryState

# -----------------------------------------------------------------------------
# Count Popup Component
# -----------------------------------------------------------------------------


def _count_option() -> rx.Component:
    return rx.vstack(
        rx.slider(
            name="count_slider",
            step=1,
            min_=1,
            max=ImageGalleryState.count_options.length(),
            size="1",
            orientation="horizontal",
            width="200px",
            default_value=ImageGalleryState.selected_count,
            on_change=ImageGalleryState.set_selected_count.throttle(100),
        ),
        rx.text(f"Anzahl der Bilder: {ImageGalleryState.selected_count}", size="1"),
        spacing="4",
        padding="9px",
        width="100%",
    )


def count_popup() -> rx.Component:
    """Popup for selecting number of images to generate."""
    return rx.popover.root(
        rx.tooltip(
            rx.popover.trigger(
                rx.button(
                    rx.text(
                        ImageGalleryState.count_label,
                        size="2",
                        weight="medium",
                    ),
                    cursor="pointer",
                    padding="8px",
                    variant="ghost",
                    margin_left="3px",
                    margin_right="3px",
                ),
            ),
            content="Wähle die Anzahl der zu generierenden Bilder",
        ),
        rx.popover.content(
            _count_option(),
            side="top",
            align="center",
        ),
        open=ImageGalleryState.count_popup_open,
        on_open_change=lambda _: ImageGalleryState.toggle_count_popup(),
    )
