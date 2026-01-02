import reflex as rx

from appkit_imagecreator.backend.models import GeneratedImageModel
from appkit_imagecreator.state import ImageGalleryState

# -----------------------------------------------------------------------------
# Image Grid Component
# -----------------------------------------------------------------------------


def _image_card(image: GeneratedImageModel) -> rx.Component:
    """Render a single image card in the grid."""
    # Action buttons container - shown on hover
    # Each button stops event propagation via empty lambda wrapper
    action_buttons = rx.fragment(
        # X button - remove from view (top left)
        rx.box(
            rx.icon_button(
                rx.icon("x", size=14),
                size="1",
                variant="solid",
                color_scheme="gray",
                border_radius="full",
                cursor="pointer",
                on_click=lambda: ImageGalleryState.remove_image_from_view(image.id),
            ),
            position="absolute",
            top="8px",
            left="8px",
            z_index="10",
        ),
        rx.box(
            rx.hstack(
                rx.icon_button(
                    rx.icon("download", size=14),
                    size="1",
                    variant="solid",
                    color_scheme="gray",
                    border_radius="full",
                    cursor="pointer",
                    on_click=lambda: ImageGalleryState.download_image(image.id),
                ),
                rx.icon_button(
                    rx.icon("plus", size=14),
                    size="1",
                    variant="solid",
                    color_scheme="gray",
                    border_radius="full",
                    cursor="pointer",
                    on_click=lambda: ImageGalleryState.add_image_to_prompt(image.id),
                ),
                rx.icon_button(
                    rx.icon("pencil", size=14),
                    size="1",
                    variant="solid",
                    color_scheme="gray",
                    border_radius="full",
                    cursor="pointer",
                    on_click=lambda: ImageGalleryState.copy_config_to_prompt(image.id),
                ),
                rx.icon_button(
                    rx.icon("zoom-in", size=14),
                    size="1",
                    variant="solid",
                    color_scheme="gray",
                    border_radius="full",
                    cursor="pointer",
                    on_click=lambda: ImageGalleryState.open_zoom_modal(image.id),
                ),
                spacing="1",
            ),
            position="absolute",
            bottom="8px",
            right="8px",
            z_index="10",
        ),
    )

    hover_overlay = rx.box(
        action_buttons,
        position="absolute",
        inset="0",
        background="transparent",
        opacity="0",
        transition="opacity 0.2s ease-in-out",
        border_radius="8px",
        class_name="hover-overlay",
    )

    return rx.box(
        rx.image(
            src=image.image_url,
            key=f"img-{image.id}",
            width="100%",
            height="100%",
            object_fit="cover",
            loading="lazy",
            border_radius="8px",
            cursor="pointer",
        ),
        hover_overlay,
        key=f"card-{image.id}",
        position="relative",
        width="100%",
        aspect_ratio="1",
        overflow="hidden",
        border_radius="8px",
        border=f"1px solid {rx.color('gray', 4)}",
        _hover={
            "& .hover-overlay": {"opacity": "1"},
        },
    )


def _generating_card() -> rx.Component:
    """Render a loading card while image is being generated."""
    # CSS for animated gradient background
    css_code = """
@property --bg-start {
  syntax: '<color>';
  initial-value: rgba(255,255,255,0.95);
  inherits: false;
}

@property --bg-mid {
  syntax: '<color>';
  initial-value: rgba(245,245,245,0.9);
  inherits: false;
}

@property --bg-end {
  syntax: '<color>';
  initial-value: rgba(230,230,230,0.85);
  inherits: false;
}

/* 2. Apply the gradient once using the variables */
.generating-bg {
  /* Note: 400% size zooms in significantly; ensure this matches your design intent */
  background-size: 400% 400%;
  background-image: radial-gradient(
    circle at center,
    var(--bg-start) 0%,
    var(--bg-mid) 50%,
    var(--bg-end) 100%
  );
  animation: bgCycle 10s linear infinite;
}

/* 3. Animate only the variable values */
@keyframes bgCycle {
  0% {
    --bg-start: rgba(255,255,255,0.95);
    --bg-mid:   rgba(245,245,245,0.9);
    --bg-end:   rgba(230,230,230,0.85);
  }
  33% {
    --bg-start: rgba(255,240,230,0.95);
    --bg-mid:   rgba(255,220,200,0.9);
    --bg-end:   rgba(255,200,170,0.85);
  }
  66% {
    --bg-start: rgba(230,245,255,0.95);
    --bg-mid:   rgba(200,230,255,0.9);
    --bg-end:   rgba(170,215,255,0.85);
  }
  100% {
    --bg-start: rgba(255,255,255,0.95);
    --bg-mid:   rgba(245,245,245,0.9);
    --bg-end:   rgba(230,230,230,0.85);
  }
}
"""

    return rx.box(
        rx.box(
            # Gradient background with blur effect
            rx.el.style(css_code),
            rx.box(
                # This box renders the animated gradient via the class above.
                class_name="generating-bg",
                position="absolute",
                inset="0",
                border_radius="8px",
            ),
            # Content overlay
            rx.vstack(
                rx.text(
                    ImageGalleryState.generating_prompt,
                    size="2",
                    color=rx.color("gray", 11),
                    text_align="center",
                    max_width="80%",
                    overflow="hidden",
                    text_overflow="ellipsis",
                    style={
                        "display": "-webkit-box",
                        "-webkit-line-clamp": "4",
                        "-webkit-box-orient": "vertical",
                    },
                ),
                position="absolute",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                width="100%",
                padding="16px",
                align="center",
                justify="center",
            ),
            # Cancel button (x)
            rx.icon_button(
                rx.icon("x", size=14),
                size="1",
                variant="solid",
                color_scheme="gray",
                position="absolute",
                top="8px",
                left="8px",
                border_radius="full",
                cursor="pointer",
                on_click=ImageGalleryState.cancel_generation,
            ),
            # Edit button at bottom
            rx.box(
                rx.icon("pencil", size=14, color=rx.color("gray", 9)),
                position="absolute",
                bottom="8px",
                right="8px",
                cursor="not-allowed",
                opacity="0.5",
            ),
            position="relative",
            width="100%",
            aspect_ratio="1",
            overflow="hidden",
            border_radius="8px",
            border=f"1px solid {rx.color('gray', 4)}",
        ),
        width="100%",
    )


def image_grid() -> rx.Component:
    """Scrollable grid of generated images."""
    return rx.cond(
        ImageGalleryState.loading_images,
        rx.center(
            rx.spinner(size="3"),
            width="100%",
            padding="64px",
        ),
        rx.cond(
            ImageGalleryState.has_images | ImageGalleryState.is_generating,
            rx.box(
                rx.box(
                    # Show generating card first when generating
                    rx.cond(
                        ImageGalleryState.is_generating,
                        _generating_card(),
                    ),
                    # Then show existing images
                    rx.foreach(ImageGalleryState.images, _image_card),
                    style={
                        "display": "grid",
                        "grid-template-columns": (
                            "repeat(auto-fill, minmax(300px, 1fr))"
                        ),
                        "gap": "16px",
                    },
                ),
                width="100%",
                padding="24px",
                padding_bottom="200px",  # Space for floating input
            ),
            rx.center(
                rx.vstack(
                    rx.icon("image", size=48, color=rx.color("gray", 8)),
                    rx.text(
                        "No images yet",
                        size="3",
                        color=rx.color("gray", 9),
                    ),
                    rx.text(
                        "Start by entering a prompt below",
                        size="2",
                        color=rx.color("gray", 8),
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                min_height="400px",
            ),
        ),
    )


# -----------------------------------------------------------------------------
# Image Zoom Modal Component
# -----------------------------------------------------------------------------


def image_zoom_modal() -> rx.Component:
    """Modal for viewing image in full size with details."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.close(
                rx.icon_button(
                    rx.icon("x", size=20),
                    variant="ghost",
                    size="2",
                    position="absolute",
                    top="16px",
                    right="16px",
                    z_index="10",
                    cursor="pointer",
                ),
            ),
            rx.flex(
                # Image side
                rx.box(
                    rx.cond(
                        ImageGalleryState.zoom_image.is_not_none(),
                        rx.image(
                            src=ImageGalleryState.zoom_image.image_url,
                            max_width="100%",
                            max_height="80vh",
                            object_fit="contain",
                            border_radius="8px",
                        ),
                    ),
                    flex="2",
                    display="flex",
                    justify_content="center",
                    align_items="center",
                    padding="24px",
                ),
                # Details side
                rx.box(
                    rx.vstack(
                        rx.cond(
                            ImageGalleryState.zoom_image.is_not_none(),
                            rx.vstack(
                                rx.text(
                                    ImageGalleryState.zoom_image.prompt,
                                    size="3",
                                    line_height="1.6",
                                    weight="medium",
                                ),
                                rx.cond(
                                    ImageGalleryState.zoom_image.enhanced_prompt,
                                    rx.box(
                                        rx.text(
                                            "Optimierter Prompt:",
                                            size="2",
                                            color=rx.color("gray", 9),
                                            weight="medium",
                                        ),
                                        rx.text(
                                            ImageGalleryState.zoom_image.enhanced_prompt,
                                            size="2",
                                            color=rx.color("gray", 11),
                                            line_height="1.5",
                                        ),
                                        margin_top="8px",
                                    ),
                                ),
                                rx.separator(size="4"),
                                rx.hstack(
                                    rx.text(
                                        "Modell:",
                                        size="2",
                                        color=rx.color("gray", 9),
                                    ),
                                    rx.text(
                                        ImageGalleryState.zoom_image.model,
                                        size="2",
                                    ),
                                    spacing="2",
                                ),
                                rx.hstack(
                                    rx.text(
                                        "Qualität:",
                                        size="2",
                                        color=rx.color("gray", 9),
                                    ),
                                    rx.text(
                                        rx.cond(
                                            ImageGalleryState.zoom_image.quality,
                                            ImageGalleryState.zoom_image.quality,
                                            "auto",
                                        ),
                                        size="2",
                                    ),
                                    spacing="2",
                                ),
                                rx.hstack(
                                    rx.text(
                                        "Größe:",
                                        size="2",
                                        color=rx.color("gray", 9),
                                    ),
                                    rx.text(
                                        f"{ImageGalleryState.zoom_image.width}x"
                                        f"{ImageGalleryState.zoom_image.height}",
                                        size="2",
                                    ),
                                    spacing="2",
                                ),
                                spacing="3",
                                align="start",
                                width="100%",
                            ),
                        ),
                        height="100%",
                        justify="start",
                        padding="24px",
                        padding_top="48px",
                    ),
                    flex="1",
                    min_width="300px",
                    border_left=f"1px solid {rx.color('gray', 5)}",
                    background=rx.color("gray", 2),
                ),
                direction="row",
                width="100%",
                height="100%",
            ),
            max_width="90vw",
            width="1200px",
            max_height="90vh",
            padding="0",
            overflow="hidden",
        ),
        open=ImageGalleryState.zoom_modal_open,
        on_open_change=lambda _: ImageGalleryState.close_zoom_modal(),
    )
