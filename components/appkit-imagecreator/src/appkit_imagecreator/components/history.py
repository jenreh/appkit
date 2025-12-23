# -----------------------------------------------------------------------------
# History Drawer Component
# -----------------------------------------------------------------------------
import reflex as rx

import appkit_mantine as mn
from appkit_imagecreator.backend.gallery_models import GeneratedImageModel
from appkit_imagecreator.gallery_state import ImageGalleryState


def _history_image_card(image: GeneratedImageModel) -> rx.Component:
    """Render a single image card in the history drawer.

    Shows only X button on hover (no pencil/edit button).
    Clicking the image adds it to the main grid.
    """
    delete_button = rx.icon_button(
        rx.icon("x", size=14),
        size="1",
        variant="solid",
        color_scheme="red",
        position="absolute",
        top="4px",
        right="4px",
        border_radius="full",
        cursor="pointer",
        z_index="10",
        on_click=lambda: ImageGalleryState.delete_image_from_db(image.id),
    )

    hover_overlay = rx.cond(
        ImageGalleryState.deleting_image_id != image.id,
        rx.box(
            delete_button,
            position="absolute",
            inset="0",
            background="rgba(0,0,0,0.3)",
            opacity="0",
            transition="opacity 0.2s ease-in-out",
            border_radius="6px",
            class_name="history-hover-overlay",
        ),
        rx.fragment(),
    )

    deleting_overlay = rx.cond(
        ImageGalleryState.deleting_image_id == image.id,
        rx.box(
            rx.center(
                rx.spinner(size="3", color="white"),
                width="100%",
                height="100%",
            ),
            position="absolute",
            inset="0",
            background="rgba(0,0,0,0.6)",
            border_radius="6px",
            z_index="20",
            pointer_events="none",
        ),
        rx.fragment(),
    )

    return rx.box(
        rx.box(
            rx.image(
                src=image.image_url,
                width="100%",
                height="100%",
                object_fit="cover",
                loading="lazy",
                border_radius="6px",
                cursor="pointer",
            ),
            hover_overlay,
            deleting_overlay,
            position="relative",
            width="100%",
            aspect_ratio="1",
            overflow="hidden",
            border_radius="6px",
            _hover={
                "& .history-hover-overlay": {"opacity": "1"},
            },
            on_click=lambda: ImageGalleryState.add_history_image_to_grid(image.id),
        ),
        width="100%",
    )


def _history_date_group(
    date_label: str, images: list[GeneratedImageModel]
) -> rx.Component:
    """Render a group of images for a specific date."""
    return rx.vstack(
        rx.heading(
            date_label,
            size="5",
            weight="bold",
            color=rx.color("gray", 12),
            padding_left="12px",
            padding_top="8px",
            padding_bottom="8px",
        ),
        rx.box(
            rx.foreach(
                images,
                _history_image_card,
            ),
            display="grid",
            grid_template_columns="repeat(3, 1fr)",
            gap="8px",
            padding_left="12px",
            padding_right="12px",
            padding_bottom="16px",
        ),
        width="100%",
        spacing="0",
        align="start",
    )


def history_drawer() -> rx.Component:
    """History drawer using rx.drawer that slides in from the right.

    Shows all images of the user grouped by date with delete capability.
    Clicking an image adds it to the main grid.
    """
    drawer_content = rx.vstack(
        rx.cond(
            ImageGalleryState.history_images.length() > 0,
            rx.box(
                rx.foreach(
                    ImageGalleryState.history_images_by_date,
                    lambda group: _history_date_group(group[0], group[1]),
                ),
                width="100%",
            ),
            rx.center(
                rx.vstack(
                    rx.icon("image-off", size=32, color=rx.color("gray", 8)),
                    rx.text(
                        "Noch keine Bilder in der Historie",
                        size="2",
                        color=rx.color("gray", 9),
                    ),
                    spacing="2",
                    align="center",
                ),
                flex="1",
                width="100%",
            ),
        ),
        width="100%",
        height="calc(100vh - 60px)",
        background=rx.color("gray", 1),
        display="flex",
        padding="0",
        margin="0",
        flex_direction="column",
        overflow_y="auto",
    )

    return mn.drawer(
        drawer_content,
        title="Historie",
        position="right",
        offset="9px",
        radius="md",
        overlay_props={"backgroundOpacity": 0.5, "blur": 4},
        with_close_button=True,
        close_on_click_outside=True,
        opened=ImageGalleryState.history_drawer_open,
        on_close=ImageGalleryState.close_history_drawer,
    )
