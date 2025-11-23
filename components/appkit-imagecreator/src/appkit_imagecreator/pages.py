import reflex as rx

from appkit_imagecreator.components.canvas import (
    button_props,
    download_button,
    image_list,
    image_ui,
)
from appkit_imagecreator.components.sidebar import sidebar


def image_generator_page() -> rx.Component:
    return rx.flex(
        sidebar(),
        rx.scroll_area(
            rx.center(
                image_ui(),
                max_width="95%",
                max_height="95%",
                align="center",
                id="image-ui",
                padding=["1em", "1em", "1em", "3em"],
            ),
            width="100%",
            height="100vh",
        ),
        rx.box(
            image_list(),
            position="fixed",
            bottom="1em",
            right="1em",
            z_index="999",
        ),
        rx.box(
            rx.hstack(
                download_button(button_props),
                justify="end",
                align="center",
            ),
            position="fixed",
            top="1em",
            right="1em",
            z_index="999",
        ),
        flex_direction=["column", "column", "column", "row"],
        position="relative",
        width="100%",
        height="100%",
        margin_top="-2.5em",
    )
