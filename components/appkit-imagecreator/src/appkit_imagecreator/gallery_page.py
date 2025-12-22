"""Image Gallery page components for the new image creator UI.

This module provides the UI components for the image gallery:
- Scrollable image grid with delete buttons
- Floating prompt input with toolbar
- Style/size/quality/count popup menus
- Image zoom modal
- History drawer
"""

import reflex as rx

from appkit_imagecreator.backend.gallery_models import GeneratedImageModel
from appkit_imagecreator.gallery_state import ImageGalleryState
from appkit_ui.components.header import header

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
    """Popup for selecting image style."""
    return rx.popover.root(
        rx.popover.trigger(
            rx.hstack(
                rx.icon("palette", size=20, color=rx.color("gray", 11)),
                rx.cond(
                    ImageGalleryState.selected_style != "",
                    rx.text(
                        ImageGalleryState.selected_style,
                        size="2",
                        color=rx.color("gray", 11),
                    ),
                ),
                cursor="pointer",
                spacing="2",
                align="center",
                padding="8px",
                border_radius="8px",
                _hover={"background": rx.color("gray", 3)},
            ),
        ),
        rx.popover.content(
            rx.vstack(
                rx.text("Style", weight="medium", size="3"),
                rx.separator(size="4"),
                rx.flex(
                    rx.foreach(
                        ImageGalleryState.styles_preset,
                        _style_item,
                    ),
                    wrap="wrap",
                    gap="3",
                    max_width="320px",
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


def _quality_option(quality: str) -> rx.Component:
    """Render a quality option item."""
    return rx.box(
        rx.hstack(
            rx.cond(
                ImageGalleryState.selected_quality == quality,
                rx.icon("check", size=16, color=rx.color("accent", 9)),
                rx.box(width="16px"),
            ),
            rx.text(quality, size="2"),
            spacing="2",
            align="center",
            width="100%",
        ),
        padding="8px 12px",
        cursor="pointer",
        border_radius="4px",
        _hover={"background": rx.color("gray", 3)},
        on_click=ImageGalleryState.set_selected_quality(quality),
    )


def config_popup() -> rx.Component:
    """Popup for selecting size and quality."""
    return rx.popover.root(
        rx.popover.trigger(
            rx.box(
                rx.icon("sliders-horizontal", size=20, color=rx.color("gray", 11)),
                cursor="pointer",
                padding="8px",
                border_radius="8px",
                _hover={"background": rx.color("gray", 3)},
            ),
        ),
        rx.popover.content(
            rx.vstack(
                # Size section
                rx.text("Size", weight="medium", size="2", color=rx.color("gray", 10)),
                rx.vstack(
                    rx.foreach(ImageGalleryState.size_options, _size_option),
                    spacing="1",
                    width="100%",
                ),
                rx.separator(size="4"),
                # Quality section
                rx.text(
                    "Quality", weight="medium", size="2", color=rx.color("gray", 10)
                ),
                rx.vstack(
                    rx.foreach(ImageGalleryState.quality_options, _quality_option),
                    spacing="1",
                    width="100%",
                ),
                rx.separator(size="4"),
                # Advanced section (placeholder)
                rx.text(
                    "Advanced",
                    weight="medium",
                    size="2",
                    color=rx.color("gray", 10),
                    cursor="pointer",
                    _hover={"color": rx.color("gray", 12)},
                ),
                spacing="3",
                padding="4px",
                min_width="200px",
            ),
            side="top",
            align="center",
        ),
        open=ImageGalleryState.config_popup_open,
        on_open_change=lambda _: ImageGalleryState.toggle_config_popup(),
    )


# -----------------------------------------------------------------------------
# Count Popup Component
# -----------------------------------------------------------------------------


def _count_option(count: int) -> rx.Component:
    """Render a count option item."""
    return rx.box(
        rx.hstack(
            rx.cond(
                ImageGalleryState.selected_count == count,
                rx.icon("check", size=16, color=rx.color("accent", 9)),
                rx.box(width="16px"),
            ),
            rx.text(f"{count}x", size="2"),
            spacing="2",
            align="center",
        ),
        padding="8px 16px",
        cursor="pointer",
        border_radius="4px",
        _hover={"background": rx.color("gray", 3)},
        on_click=ImageGalleryState.set_selected_count(count),
    )


def count_popup() -> rx.Component:
    """Popup for selecting number of images to generate."""
    return rx.popover.root(
        rx.popover.trigger(
            rx.box(
                rx.text(
                    ImageGalleryState.count_label,
                    size="2",
                    weight="medium",
                    color=rx.color("gray", 11),
                ),
                cursor="pointer",
                padding="8px 12px",
                border_radius="8px",
                _hover={"background": rx.color("gray", 3)},
            ),
        ),
        rx.popover.content(
            rx.vstack(
                rx.foreach(ImageGalleryState.count_options, _count_option),
                spacing="1",
                padding="4px",
            ),
            side="top",
            align="center",
        ),
        open=ImageGalleryState.count_popup_open,
        on_open_change=lambda _: ImageGalleryState.toggle_count_popup(),
    )


# -----------------------------------------------------------------------------
# Model Selector Component
# -----------------------------------------------------------------------------


def model_selector() -> rx.Component:
    """Dropdown for selecting the image generation model."""
    return rx.select.root(
        rx.select.trigger(
            placeholder="Model",
            variant="ghost",
            size="2",
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
                rx.text_area(
                    placeholder="Describe the image you want to create...",
                    value=ImageGalleryState.prompt,
                    on_change=ImageGalleryState.set_prompt,
                    width="100%",
                    min_height="60px",
                    max_height="120px",
                    resize="vertical",
                    border="none",
                    outline="none",
                    background="transparent",
                    _focus={"outline": "none", "border": "none"},
                ),
                rx.cond(
                    ImageGalleryState.is_generating,
                    rx.button(
                        rx.spinner(size="3"),
                        variant="solid",
                        size="3",
                        border_radius="full",
                        disabled=True,
                    ),
                    rx.icon_button(
                        rx.icon("arrow-up", size=20),
                        variant="solid",
                        size="3",
                        border_radius="full",
                        on_click=ImageGalleryState.generate_images,
                        disabled=ImageGalleryState.prompt == "",
                    ),
                ),
                width="100%",
                align="end",
                spacing="3",
            ),
            rx.hstack(
                style_popup(),
                config_popup(),
                count_popup(),
                rx.tooltip(
                    rx.box(
                        rx.hstack(
                            rx.switch(
                                checked=ImageGalleryState.enhance_prompt,
                                on_change=ImageGalleryState.set_enhance_prompt,
                                size="1",
                            ),
                            rx.icon(
                                "sparkles",
                                size=14,
                                color=rx.cond(
                                    ImageGalleryState.enhance_prompt,
                                    rx.color("blue", 10),
                                    rx.color("gray", 9),
                                ),
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
                ),
                rx.box(
                    rx.icon("paperclip", size=18, color=rx.color("gray", 9)),
                    cursor="not-allowed",
                    opacity="0.5",
                    padding="8px",
                ),
                rx.spacer(),
                model_selector(),
                width="100%",
                align="center",
                spacing="1",
            ),
            width="100%",
            spacing="2",
        ),
        background=rx.color("gray", 1),
        border=f"1px solid {rx.color('gray', 5)}",
        border_radius="16px",
        padding="16px",
        box_shadow="0 4px 24px rgba(0, 0, 0, 0.08)",
        width="100%",
        max_width="700px",
    )


# -----------------------------------------------------------------------------
# Image Grid Component
# -----------------------------------------------------------------------------


def _image_card(image: GeneratedImageModel) -> rx.Component:
    """Render a single image card in the grid."""
    # Action buttons container - shown on hover
    action_buttons = rx.fragment(
        # X button - remove from view (top left)
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
            z_index="10",
            on_click=lambda: ImageGalleryState.remove_image_from_view(image.id),
        ),
        # Action buttons overlay (bottom right)
        rx.hstack(
            # Download button
            rx.icon_button(
                rx.icon("download", size=14),
                size="1",
                variant="solid",
                color_scheme="gray",
                border_radius="full",
                cursor="pointer",
                on_click=lambda: ImageGalleryState.download_image(image.id),
            ),
            # Add to prompt button
            rx.icon_button(
                rx.icon("plus", size=14),
                size="1",
                variant="solid",
                color_scheme="gray",
                border_radius="full",
                cursor="pointer",
                on_click=lambda: ImageGalleryState.add_image_to_prompt(image.id),
            ),
            # Copy config button
            rx.icon_button(
                rx.icon("pencil", size=14),
                size="1",
                variant="solid",
                color_scheme="gray",
                border_radius="full",
                cursor="pointer",
                on_click=lambda: ImageGalleryState.copy_config_to_prompt(image.id),
            ),
            position="absolute",
            bottom="8px",
            right="8px",
            spacing="1",
            z_index="10",
        ),
    )

    # Hover overlay container
    gradient_bg = (
        "linear-gradient(to bottom, rgba(0,0,0,0.3) 0%, "
        "transparent 30%, transparent 70%, rgba(0,0,0,0.3) 100%)"
    )
    hover_overlay = rx.box(
        action_buttons,
        position="absolute",
        inset="0",
        background=gradient_bg,
        opacity="0",
        transition="opacity 0.2s ease-in-out",
        border_radius="8px",
        class_name="hover-overlay",
    )

    return rx.box(
        rx.box(
            rx.image(
                src=image.image_url,
                width="100%",
                height="100%",
                object_fit="cover",
                loading="lazy",
                border_radius="8px",
                cursor="pointer",
                on_click=ImageGalleryState.open_zoom_modal(image.id),
            ),
            hover_overlay,
            position="relative",
            width="100%",
            aspect_ratio="1",
            overflow="hidden",
            border_radius="8px",
            _hover={
                "& .hover-overlay": {"opacity": "1"},
            },
        ),
        width="100%",
    )


def _generating_card() -> rx.Component:
    """Render a loading card while image is being generated."""
    # CSS for animated gradient background
    css_code = """
@keyframes bgCycle {
  0% {
    background: radial-gradient(circle at center,
      rgba(255,255,255,0.95) 0%,
      rgba(245,245,245,0.9) 50%,
      rgba(230,230,230,0.85) 100%);
  }
  33% {
    background: radial-gradient(circle at center,
      rgba(255,240,230,0.95) 0%,
      rgba(255,220,200,0.9) 50%,
      rgba(255,200,170,0.85) 100%);
  }
  66% {
    background: radial-gradient(circle at center,
      rgba(230,245,255,0.95) 0%,
      rgba(200,230,255,0.9) 50%,
      rgba(170,215,255,0.85) 100%);
  }
  100% {
    background: radial-gradient(circle at center,
      rgba(255,255,255,0.95) 0%,
      rgba(245,245,245,0.9) 50%,
      rgba(230,230,230,0.85) 100%);
  }
}
.generating-bg {
  background-size: 400% 400%;
  animation: bgCycle 10s linear infinite;
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


def zoom_modal() -> rx.Component:
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
                                    rx.text(
                                        "Größe:",
                                        size="2",
                                        color=rx.color("gray", 9),
                                        margin_left="16px",
                                    ),
                                    rx.text(
                                        f"{ImageGalleryState.zoom_image.width}x"
                                        f"{ImageGalleryState.zoom_image.height}",
                                        size="2",
                                    ),
                                    spacing="2",
                                    wrap="wrap",
                                ),
                                spacing="4",
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


# -----------------------------------------------------------------------------
# Header Component
# -----------------------------------------------------------------------------


def gallery_header() -> rx.Component:
    """Header with title and action buttons."""
    return rx.hstack(
        rx.text("Images", size="5", weight="medium"),
        rx.spacer(),
        rx.hstack(
            rx.button(
                rx.icon("eraser", size=16),
                rx.text("Clear"),
                variant="ghost",
                size="2",
                color_scheme="gray",
                on_click=ImageGalleryState.clear_all_images,
                cursor="pointer",
            ),
            rx.button(
                rx.icon("history", size=16),
                rx.text("History"),
                variant="ghost",
                size="2",
                color_scheme="gray",
                on_click=ImageGalleryState.toggle_history_drawer,
                cursor="pointer",
            ),
            spacing="2",
        ),
        width="100%",
        padding="16px 24px",
        border_bottom=f"1px solid {rx.color('gray', 4)}",
        align="center",
    )


# -----------------------------------------------------------------------------
# Main Gallery Page Component
# -----------------------------------------------------------------------------


def image_gallery_page() -> rx.Component:
    """Main image gallery page component."""
    return rx.box(
        # Header
        header("Bildgenerator"),
        # Main content area with scrollable grid
        rx.scroll_area(
            image_grid(),
            height="calc(100vh - 60px)",
            width="100%",
        ),
        # Floating prompt input
        rx.box(
            prompt_input_bar(),
            position="fixed",
            bottom="24px",
            left="50%",
            transform="translateX(-50%)",
            width="100%",
            max_width="700px",
            padding="0 24px",
            z_index="100",
        ),
        # Zoom modal
        zoom_modal(),
        # Initialize on mount
        on_mount=ImageGalleryState.initialize,
        width="100%",
        height="100vh",
        position="relative",
        background=rx.color("gray", 1),
    )
