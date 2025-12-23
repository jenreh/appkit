import reflex as rx

from appkit_imagecreator.gallery_state import ImageGalleryState

# -----------------------------------------------------------------------------
# Style Popup Component
# -----------------------------------------------------------------------------


def _style_item(style_data: tuple[str, dict]) -> rx.Component:
    """Render a single style option in the popup."""
    style_name = style_data[0]
    style_info = style_data[1]

    return rx.tooltip(
        rx.box(
            rx.image(
                src=style_info["path"],
                width="80px",
                height="80px",
                object_fit="cover",
                border_radius="8px",
                cursor="pointer",
                border=rx.cond(
                    ImageGalleryState.selected_style == style_name,
                    f"3px solid {rx.color('accent', 9)}",
                    "3px solid transparent",
                ),
                opacity=rx.cond(
                    ImageGalleryState.selected_style == style_name,
                    "1",
                    "0.8",
                ),
                _hover={"opacity": "1", "transform": "scale(1.05)"},
                transition="all 0.2s ease",
            ),
            on_click=ImageGalleryState.set_selected_style(style_name),
        ),
        content=style_name,
    )


def style_popup() -> rx.Component:
    """Popup for selecting image style with dynamic image trigger."""
    return rx.popover.root(
        rx.popover.trigger(
            # Ein rx.box Container sorgt für konsistentes Layout als Button
            rx.box(
                rx.cond(
                    ImageGalleryState.selected_style != "",
                    # FALL 1: Style ausgewählt -> Zeige das Bild des Styles
                    rx.image(
                        src=ImageGalleryState.selected_style_path,
                        width="24px",
                        height="24px",
                        object_fit="cover",
                        border_radius="4px",
                        alt=ImageGalleryState.selected_style,
                    ),
                    # FALL 2: Kein Style -> Zeige das Palette-Icon
                    rx.icon("palette", size=20, color=rx.color("gray", 11)),
                ),
                # Styling für den Trigger-Button selbst
                cursor="pointer",
                padding="8px",
                border_radius="8px",
                display="flex",
                align_items="center",
                justify_content="center",
                _hover={"background": rx.color("gray", 3)},
                transition="background 0.2s",
            ),
        ),
        rx.popover.content(
            rx.vstack(
                rx.flex(
                    rx.foreach(
                        ImageGalleryState.styles_preset,
                        _style_item,
                    ),
                    wrap="wrap",
                    gap="3",
                    max_width="240px",
                ),
                spacing="3",
                padding="4px",
            ),
            side="top",
            align="start",
        ),
        open=ImageGalleryState.style_popup_open,
        on_open_change=lambda _: ImageGalleryState.toggle_style_popup(),
    )
