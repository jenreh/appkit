import reflex as rx

from appkit_imagecreator.components.react_zoom import image_zoom
from appkit_imagecreator.states import GeneratorState

image_props = {
    "decoding": "auto",
    "loading": "eager",
    "vertical_align": "middle",
    "object_fit": "contain",
    "width": "100%",
    "height": ["400px", "500px", "650px", "850px"],
}

button_props = {
    "size": "2",
    "cursor": "pointer",
    "variant": "outline",
}


def _image_list_item(image: str) -> rx.Component:
    return rx.skeleton(
        rx.box(
            rx.image(
                src=image,
                width="100%",
                height="100%",
                decoding="auto",
                style={
                    "transform": rx.cond(
                        image == rx.get_upload_url(GeneratorState.output_image),
                        "scale(0.875)",
                        "",
                    ),
                    "filter": rx.cond(
                        image == rx.get_upload_url(GeneratorState.output_image),
                        "",
                        "brightness(.75)",
                    ),
                },
                loading="lazy",
                alt="Output image option",
                transition="all 0.2s ease",
                object_fit="cover",
            ),
            width="auto",
            aspect_ratio="1/1",
            max_height="5em",
            max_width="5em",
            cursor="pointer",
            background=rx.color("accent", 9),
            on_click=GeneratorState.set_output_image(image),
        ),
        loading=GeneratorState.is_generating,
    )


def image_list() -> rx.Component:
    return rx.scroll_area(
        rx.hstack(
            rx.foreach(
                GeneratorState.output_list,
                _image_list_item,
            ),
            spacing="4",
            width="100%",
            align="center",
        ),
        display=rx.cond(
            GeneratorState.output_list,
            "flex",
            "none",
        ),
        type="auto",
        scrollbars="horizontal",
    )


def download_button(button_props: dict[str, str]) -> rx.Component:
    return rx.cond(
        GeneratorState.is_downloading,
        rx.icon_button(
            rx.spinner(size="3"),
            **button_props,
            color_scheme="blue",
        ),
        rx.icon_button(
            rx.icon("download", size=20),
            **button_props,
            color_scheme="gray",
            on_click=GeneratorState.download_image,
        ),
    )


def image_ui() -> rx.Component:
    return rx.cond(
        GeneratorState.is_generating,
        rx.skeleton(
            rx.box(
                rx.image(
                    src=rx.get_upload_url(GeneratorState.output_image), **image_props
                )
            ),
            loading=GeneratorState.is_generating,
        ),
        image_zoom(rx.image(src=GeneratorState.output_image, **image_props)),
    )
