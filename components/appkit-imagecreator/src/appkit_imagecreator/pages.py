"""Image Gallery page components for the new image creator UI.

This module provides the UI components for the image gallery:
- Scrollable image grid with delete buttons
- Floating prompt input with toolbar
- Style/size/quality/count popup menus
- Image zoom modal
- History drawer
"""

import reflex as rx

from appkit_imagecreator.components.history import history_drawer
from appkit_imagecreator.components.images import image_grid, image_zoom_modal
from appkit_imagecreator.components.prompt import prompt_input_bar
from appkit_imagecreator.state import ImageGalleryState
from appkit_ui.components.header import header


def gallery_header() -> rx.Component:
    """Header with title and action buttons."""
    return rx.hstack(
        rx.spacer(),
        rx.button(
            rx.icon("paintbrush", size=16),
            rx.text(" Raster leeren"),
            variant="ghost",
            size="2",
            color_scheme="gray",
            on_click=ImageGalleryState.clear_grid_view,
            cursor="pointer",
            margin_right="12px",
        ),
        rx.button(
            rx.icon("history", size=16),
            rx.text(" Historie"),
            variant="ghost",
            size="2",
            color_scheme="gray",
            on_click=ImageGalleryState.toggle_history,
            cursor="pointer",
            margin_right="12px",
        ),
        spacing="3",
        width="100%",
    )


def image_generator_page() -> rx.Component:
    """Main image gallery page component."""
    return rx.box(
        header("Bildgenerator", header_items=gallery_header()),
        rx.scroll_area(
            image_grid(),
            height="calc(100vh - 60px)",
            width="100%",
        ),
        rx.box(
            prompt_input_bar(),
            position="fixed",
            bottom="24px",
            left="calc(50% + 9em)",
            transform="translateX(-50%)",
            width="100%",
            max_width="700px",
            padding="0 24px",
            z_index="100",
        ),
        image_zoom_modal(),
        history_drawer(),
        on_mount=ImageGalleryState.initialize,
        width="100%",
        height="100vh",
        position="relative",
        background=rx.color("gray", 1),
    )
