import reflex as rx

import appkit_mantine as mn
from appkit_imagecreator.backend.gallery_models import GeneratedImageModel
from appkit_imagecreator.components.count import count_popup
from appkit_imagecreator.components.image_props import image_props_popup
from appkit_imagecreator.components.styles import style_popup
from appkit_imagecreator.gallery_state import ImageGalleryState

# -----------------------------------------------------------------------------
# Prompt Input Component
# -----------------------------------------------------------------------------


def _selected_image_thumbnail(image: GeneratedImageModel) -> rx.Component:
    """Render a small thumbnail for selected images in the prompt area."""
    return rx.box(
        rx.image(
            src=image.image_url,
            width="48px",
            height="48px",
            object_fit="cover",
            border_radius="6px",
        ),
        rx.icon_button(
            rx.icon("x", size=10),
            size="1",
            variant="solid",
            color_scheme="gray",
            position="absolute",
            top="-6px",
            right="-6px",
            border_radius="full",
            cursor="pointer",
            on_click=lambda: ImageGalleryState.remove_image_from_prompt(image.id),
        ),
        position="relative",
    )


def _submit() -> rx.Component:
    return rx.fragment(
        rx.cond(
            ~ImageGalleryState.is_generating,
            rx.button(
                rx.icon("arrow-right", size=18),
                id="prompt-submit",
                name="prompt_submit",
                type="submit",
                disabled=ImageGalleryState.prompt == "",
                on_click=ImageGalleryState.generate_images,
            ),
            rx.button(
                rx.icon("x", size=18),
                color_scheme="tomato",
                id="prompt-submit",
                name="prompt_submit",
                type="submit",
                on_click=ImageGalleryState.cancel_generation,
            ),
        )
    )


def _model_selector() -> rx.Component:
    """Dropdown for selecting the image generation model."""
    return rx.select.root(
        rx.select.trigger(
            placeholder="Model",
            variant="ghost",
            margin_left="3px",
            size="1",
        ),
        rx.select.content(
            rx.foreach(
                ImageGalleryState.generators,
                lambda gen: rx.select.item(gen["label"], value=gen["id"]),
            ),
            position="popper",
            side="top",
        ),
        value=ImageGalleryState.generator,
        on_change=ImageGalleryState.set_generator,
        size="2",
    )


def _enhance_prompt_checkbox() -> rx.Component:
    return rx.tooltip(
        rx.box(
            rx.hstack(
                rx.icon(
                    "sparkles",
                    size=14,
                    color=rx.cond(
                        ImageGalleryState.enhance_prompt,
                        rx.color("blue", 10),
                        rx.color("gray", 9),
                    ),
                ),
                rx.switch(
                    checked=ImageGalleryState.enhance_prompt,
                    on_change=ImageGalleryState.set_enhance_prompt,
                    size="1",
                ),
                spacing="1",
                align="center",
            ),
            cursor="pointer",
            padding="6px 10px",
            border_radius="8px",
            _hover={"background": rx.color("gray", 3)},
        ),
        content="Prompt automatisch verbessern (KI optimiert den Prompt)",
    )


def _reference_image_upload() -> rx.Component:
    return rx.box(
        rx.icon("paperclip", size=18, color=rx.color("gray", 9)),
        cursor="not-allowed",
        opacity="0.5",
        padding="8px",
    )


def prompt_input_bar() -> rx.Component:
    """Floating prompt input bar with toolbar icons."""
    return rx.box(
        rx.vstack(
            # Selected images row
            rx.cond(
                ImageGalleryState.selected_images.length() > 0,
                rx.hstack(
                    rx.foreach(
                        ImageGalleryState.selected_images,
                        _selected_image_thumbnail,
                    ),
                    spacing="2",
                    padding_bottom="8px",
                ),
            ),
            rx.hstack(
                mn.textarea(
                    placeholder="Beschreibe das Bild, das du erstellen möchtest...",
                    value=ImageGalleryState.prompt,
                    on_change=ImageGalleryState.set_prompt,
                    width="100%",
                    autosize=True,
                    min_rows=2,
                    max_rows=5,
                    variant="unstyled",
                ),
                width="100%",
                align="end",
                spacing="3",
            ),
            rx.hstack(
                style_popup(),
                image_props_popup(),
                count_popup(),
                _enhance_prompt_checkbox(),
                # _reference_image_upload(),
                _model_selector(),
                rx.spacer(),
                _submit(),
                width="100%",
                align="center",
                spacing="1",
            ),
            width="100%",
            spacing="2",
        ),
        background=rx.color("gray", 1),
        border=f"1px solid {rx.color('gray', 9)}",
        border_radius="9px",
        padding="9px",
        box_shadow="0 2px 12px rgba(0, 0, 0, .2)",
        width="100%",
        max_width="700px",
    )
