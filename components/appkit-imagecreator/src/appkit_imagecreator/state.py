"""State management for the image gallery.

This module contains ImageGalleryState which manages:
- Image generation and storage
- Style/quality/count popup states
- Image grid display and zoom functionality
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import httpx
import reflex as rx

from appkit_imagecreator.backend.generator_registry import generator_registry
from appkit_imagecreator.backend.models import (
    GeneratedImageData,
    GeneratedImageModel,
    GenerationInput,
    ImageGeneratorResponse,
    ImageResponseState,
)
from appkit_imagecreator.backend.repository import GeneratedImageRepository
from appkit_imagecreator.configuration import styles_preset
from appkit_user.authentication.states import UserSession

logger = logging.getLogger(__name__)

# Size options matching the screenshot
SIZE_OPTIONS: list[dict[str, str | int]] = [
    {"label": "Square (1024x1024)", "width": 1024, "height": 1024},
    {"label": "Portrait (1024x1536)", "width": 1024, "height": 1536},
    {"label": "Landscape (1536x1024)", "width": 1536, "height": 1024},
]

# Quality options
QUALITY_OPTIONS: list[str] = ["Auto", "High", "Medium", "Low"]

# Count options
COUNT_OPTIONS: list[int] = [1, 2, 3, 4]


class ImageGalleryState(rx.State):
    """State for the image gallery UI.

    Manages image generation, storage, and UI interactions including
    popup menus for style, size, quality, and count selection.
    """

    # Stored images (today's images for grid)
    images: list[GeneratedImageModel] = []
    # All images for history
    history_images: list[GeneratedImageModel] = []
    loading_images: bool = False

    # Generation state
    is_generating: bool = False
    prompt: str = ""
    generating_prompt: str = ""  # The prompt being generated (for display)

    # Style selection
    selected_style: str = ""
    style_popup_open: bool = False
    styles_preset: dict[str, dict[str, str]] = styles_preset

    # Config popup state
    config_popup_open: bool = False
    selected_size: str = "Square (1024x1024)"
    selected_width: int = 1024
    selected_height: int = 1024
    selected_quality: str = "Auto"

    # Count popup state
    count_popup_open: bool = False
    selected_count: int = 1

    # Prompt enhancement
    enhance_prompt: bool = True

    # Model selection
    generator: str = generator_registry.get_default_generator().id
    generators: list[dict[str, str]] = generator_registry.list_generators()

    # Zoom modal state
    zoom_modal_open: bool = False
    zoom_image: GeneratedImageModel | None = None

    # Selected images for prompt (image-to-image)
    selected_images: list[GeneratedImageModel] = []

    # History drawer state
    history_drawer_open: bool = False
    deleting_image_id: int

    # Initialization
    _initialized: bool = False
    _current_user_id: int = 0

    # -------------------------------------------------------------------------
    # Computed properties
    # -------------------------------------------------------------------------

    @rx.var
    def has_images(self) -> bool:
        """Check if there are any images."""
        return len(self.images) > 0

    @rx.var
    def count_label(self) -> str:
        """Label for the count selector."""
        return f"{self.selected_count}x"

    @rx.var
    def style_label(self) -> str:
        """Label showing selected style or empty."""
        return self.selected_style if self.selected_style else ""

    @rx.var
    def size_options(self) -> list[dict[str, Any]]:
        """Get available size options."""
        return SIZE_OPTIONS

    @rx.var
    def quality_options(self) -> list[str]:
        """Get available quality options."""
        return QUALITY_OPTIONS

    @rx.var
    def count_options(self) -> list[int]:
        """Get available count options."""
        return COUNT_OPTIONS

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    @rx.event(background=True)
    async def initialize(self) -> AsyncGenerator[Any, Any]:
        """Initialize the image gallery - load images from database."""
        async with self:
            if self._initialized:
                return
            self.loading_images = True
        yield

        async for _ in self._load_images():
            yield

    async def _load_images(self) -> AsyncGenerator[Any, Any]:
        """Load images from database (internal)."""
        async with self:
            user_session: UserSession = await self.get_state(UserSession)
            current_user_id = user_session.user.user_id if user_session.user else 0
            is_authenticated = await user_session.is_authenticated

            # Handle user change
            if self._current_user_id != current_user_id:
                logger.info(
                    "User changed from '%s' to '%s' - resetting state",
                    self._current_user_id or "(none)",
                    current_user_id or "(none)",
                )
                self._initialized = False
                self._current_user_id = current_user_id
                self.images = []
                self.history_images = []
                yield

            if self._initialized:
                self.loading_images = False
                yield
                return

            # Check authentication
            if not is_authenticated:
                self.images = []
                self.history_images = []
                self._current_user_id = 0
                self.loading_images = False
                yield
                return

            user_id = user_session.user.user_id if user_session.user else None

        if not user_id:
            async with self:
                self.loading_images = False
            yield
            return

        # Fetch images from database
        try:
            # Load today's images for grid
            today_images = await GeneratedImageRepository.get_today_by_user(user_id)
            # Load all images for history
            all_images = await GeneratedImageRepository.get_by_user(user_id)
            async with self:
                self.images = today_images
                self.history_images = all_images
                self._initialized = True
                logger.debug(
                    "Loaded %d today's images, %d total for user %s",
                    len(today_images),
                    len(all_images),
                    user_id,
                )
            yield
        except Exception as e:
            logger.error("Error loading images: %s", e)
            async with self:
                self.images = []
                self.history_images = []
            yield
        finally:
            async with self:
                self.loading_images = False
            yield

    # -------------------------------------------------------------------------
    # Style popup handlers
    # -------------------------------------------------------------------------

    @rx.event
    def toggle_style_popup(self) -> None:
        """Toggle the style selection popup."""
        self.style_popup_open = not self.style_popup_open
        # Close other popups
        self.config_popup_open = False
        self.count_popup_open = False

    @rx.event
    def set_selected_style(self, style: str) -> None:
        """Set the selected style."""
        self.selected_style = style if style != self.selected_style else ""
        self.style_popup_open = False

    @rx.var
    def selected_style_path(self) -> str:
        """Get the image path directly from the styles_preset dictionary."""
        style_data = self.styles_preset.get(self.selected_style, {})
        path = style_data.get("path", "")

        if path and not path.startswith(("http", "/")):
            return f"/{path}"

        return path

    @rx.event
    def close_style_popup(self) -> None:
        """Close the style popup."""
        self.style_popup_open = False

    # -------------------------------------------------------------------------
    # Config popup handlers
    # -------------------------------------------------------------------------

    @rx.event
    def toggle_config_popup(self) -> None:
        """Toggle the config popup."""
        self.config_popup_open = not self.config_popup_open
        # Close other popups
        self.style_popup_open = False
        self.count_popup_open = False

    @rx.event
    def set_selected_size(self, size_label: str) -> None:
        """Set the selected size from label."""
        self.selected_size = size_label
        for opt in SIZE_OPTIONS:
            if opt["label"] == size_label:
                self.selected_width = opt["width"]
                self.selected_height = opt["height"]
                break

    @rx.event
    def set_selected_quality(self, quality: str) -> None:
        """Set the selected quality."""
        self.selected_quality = quality

    @rx.event
    def close_config_popup(self) -> None:
        """Close the config popup."""
        self.config_popup_open = False

    # -------------------------------------------------------------------------
    # Count popup handlers
    # -------------------------------------------------------------------------

    @rx.event
    def toggle_count_popup(self) -> None:
        """Toggle the count selection popup."""
        self.count_popup_open = not self.count_popup_open
        # Close other popups
        self.style_popup_open = False
        self.config_popup_open = False

    @rx.event
    def set_selected_count(self, value: list[int | float]) -> None:
        """Set the number of images to generate."""
        self.selected_count = value[0] if value else 1
        # self.count_popup_open = False

    @rx.event
    def close_count_popup(self) -> None:
        """Close the count popup."""
        self.count_popup_open = False

    # -------------------------------------------------------------------------
    # Generator selection
    # -------------------------------------------------------------------------

    @rx.event
    def set_generator(self, generator_id: str) -> None:
        """Set the selected generator/model."""
        self.generator = generator_id

    @rx.event
    def set_enhance_prompt(self, value: bool) -> None:
        """Set the enhance_prompt flag."""
        self.enhance_prompt = value

    # -------------------------------------------------------------------------
    # Prompt handlers
    # -------------------------------------------------------------------------

    @rx.event
    def set_prompt(self, prompt: str) -> None:
        """Set the prompt text."""
        self.prompt = prompt

    @rx.event
    def cancel_generation(self) -> None:
        """Cancel the current image generation."""
        self.is_generating = False
        self.generating_prompt = ""

    # -------------------------------------------------------------------------
    # Image generation
    # -------------------------------------------------------------------------

    async def _get_image_bytes(self, img_data: GeneratedImageData) -> bytes | None:
        """Extract bytes from GeneratedImageData, fetching from URL if needed.

        Args:
            img_data: Generated image data with either bytes or external URL

        Returns:
            Raw image bytes or None if extraction failed
        """
        if img_data.image_bytes:
            return img_data.image_bytes

        if img_data.external_url:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(img_data.external_url, timeout=60.0)
                    resp.raise_for_status()
                    return resp.content
            except httpx.HTTPError as e:
                logger.error("Failed to fetch image from URL: %s", e)
                return None

        return None

    @rx.event(background=True)
    async def generate_images(  # noqa: PLR0912, PLR0915
        self,
    ) -> AsyncGenerator[Any, Any]:
        """Generate images based on current settings."""
        # Validation
        async with self:
            if not self.prompt.strip():
                yield rx.toast.warning("Bitte gib einen Prompt ein.", close_button=True)
                return

            self.is_generating = True
            self.generating_prompt = self.prompt
            self.style_popup_open = False
            self.config_popup_open = False
            self.count_popup_open = False
        yield

        try:
            # Get user info
            async with self:
                user_session: UserSession = await self.get_state(UserSession)
                user_id = user_session.user.user_id if user_session.user else None

            if not user_id:
                yield rx.toast.error(
                    "Bitte melde dich an, um Bilder zu generieren.",
                    close_button=True,
                )
                return

            # Build generation input
            async with self:
                style_prompt = ""
                if self.selected_style and self.selected_style in self.styles_preset:
                    style_prompt = (
                        "\n" + self.styles_preset[self.selected_style]["prompt"]
                    )

                full_prompt = self.prompt + style_prompt
                generation_input = GenerationInput(
                    prompt=full_prompt,
                    width=self.selected_width,
                    height=self.selected_height,
                    n=self.selected_count,
                    enhance_prompt=self.enhance_prompt,
                )
                client = generator_registry.get(self.generator)

                # Capture state values for database save
                prompt = self.prompt
                style = self.selected_style
                model = self.generator
                width = self.selected_width
                height = self.selected_height
                quality = self.selected_quality
                should_enhance = self.enhance_prompt
                count = self.selected_count

            # Generate images
            response: ImageGeneratorResponse = await client.generate(generation_input)

            if response.state != ImageResponseState.SUCCEEDED:
                async with self:
                    self.is_generating = False
                yield rx.toast.error(
                    f"Fehler beim Generieren: {response.error or 'Unbekannter Fehler'}",
                    close_button=True,
                )
                return

            if not response.generated_images:
                async with self:
                    self.is_generating = False
                yield rx.toast.error(
                    "Keine Bilder generiert.",
                    close_button=True,
                )
                return

            # Save each generated image to database
            enhanced_prompt = response.enhanced_prompt or full_prompt
            saved_count = 0

            for img_data in response.generated_images:
                image_bytes = await self._get_image_bytes(img_data)
                if not image_bytes:
                    logger.warning("Could not get bytes for generated image")
                    continue

                try:
                    saved_image = await GeneratedImageRepository.create(
                        user_id=user_id,
                        prompt=prompt,
                        model=model,
                        image_data=image_bytes,
                        content_type=img_data.content_type,
                        width=width,
                        height=height,
                        enhanced_prompt=enhanced_prompt,
                        style=style if style else None,
                        quality=quality if quality != "Auto" else None,
                        config={
                            "size": f"{width}x{height}",
                            "quality": quality,
                            "count": count,
                            "enhance_prompt": should_enhance,
                        },
                    )
                    async with self:
                        self.images = [saved_image, *self.images]
                        self.history_images = [saved_image, *self.history_images]
                    saved_count += 1
                    yield
                except Exception as e:
                    logger.error("Error saving generated image: %s", e)

            if saved_count > 0:
                yield rx.toast.success(
                    f"{saved_count} Bild(er) erfolgreich generiert!",
                    close_button=True,
                )
            else:
                yield rx.toast.error(
                    "Keine Bilder konnten gespeichert werden.",
                    close_button=True,
                )

        except Exception as e:
            logger.exception("Error generating images")
            yield rx.toast.error(
                f"Fehler beim Generieren: {e!s}",
                close_button=True,
            )
        finally:
            async with self:
                self.is_generating = False
                self.generating_prompt = ""
            yield

    # -------------------------------------------------------------------------
    # Image management
    # -------------------------------------------------------------------------

    @rx.event()
    async def clear_grid_view(self) -> AsyncGenerator[Any, Any]:
        """Clear all images for the current user."""
        self.images = []
        self.zoom_modal_open = False
        self.zoom_image = None

    # -------------------------------------------------------------------------
    # Zoom modal handlers
    # -------------------------------------------------------------------------

    @rx.event
    def open_zoom_modal(self, image_id: int) -> None:
        """Open the zoom modal for a specific image."""
        for img in self.images:
            if img.id == image_id:
                self.zoom_image = img
                self.zoom_modal_open = True
                break

    @rx.event
    def close_zoom_modal(self) -> None:
        """Close the zoom modal."""
        self.zoom_modal_open = False
        self.zoom_image = None

    # -------------------------------------------------------------------------
    # Image action handlers (hover actions)
    # -------------------------------------------------------------------------

    @rx.event
    def add_image_to_prompt(self, image_id: int) -> None:
        """Add an image to the selected images for image-to-image generation."""
        for img in self.images:
            if img.id == image_id:
                # Check if already selected
                if not any(s.id == image_id for s in self.selected_images):
                    self.selected_images = [*self.selected_images, img]
                break

    @rx.event
    def remove_image_from_prompt(self, image_id: int) -> None:
        """Remove an image from the selected images."""
        self.selected_images = [s for s in self.selected_images if s.id != image_id]

    @rx.event
    def copy_config_to_prompt(self, image_id: int) -> None:
        """Copy the prompt and configuration from an image to the input fields."""
        for img in self.images:
            if img.id == image_id:
                self.prompt = img.prompt
                self.selected_style = img.style or ""
                self.selected_quality = img.quality or "Auto"
                self.selected_width = img.width
                self.selected_height = img.height
                self.generator = img.model  # Set the generator/model
                # Find matching size label
                for opt in SIZE_OPTIONS:
                    if opt["width"] == img.width and opt["height"] == img.height:
                        self.selected_size = opt["label"]
                        break
                # Try to restore count and enhance_prompt from config if available
                if img.config:
                    if "count" in img.config:
                        self.selected_count = img.config["count"]
                    if "enhance_prompt" in img.config:
                        self.enhance_prompt = img.config["enhance_prompt"]
                break

    @rx.event
    def remove_image_from_view(self, image_id: int) -> None:
        """Remove an image from the current view (doesn't delete from DB)."""
        self.images = [img for img in self.images if img.id != image_id]
        # Also remove from selected if present
        self.selected_images = [s for s in self.selected_images if s.id != image_id]

    @rx.event(background=True)
    async def download_image(self, image_id: int) -> AsyncGenerator[Any, Any]:
        """Download an image file."""
        # Find the image
        image = None
        for img in self.images:
            if img.id == image_id:
                image = img
                break

        if not image:
            yield rx.toast.error("Bild nicht gefunden", close_button=True)
            return

        try:
            # Fetch image data from repository
            result = await GeneratedImageRepository.get_image_data(image_id)
            if result is None:
                yield rx.toast.error("Bilddaten nicht gefunden", close_button=True)
                return

            image_data, _ = result
            filename = f"image_{image.id}.png"
            # Download raw binary data
            yield rx.download(data=image_data, filename=filename)
        except Exception as e:
            logger.error("Error downloading image: %s", e)
            yield rx.toast.error(f"Fehler beim Download: {e!s}", close_button=True)

    # -------------------------------------------------------------------------
    # History drawer handlers
    # -------------------------------------------------------------------------

    @rx.event
    def toggle_history(self) -> None:
        """Toggle the history drawer."""
        self.history_drawer_open = not self.history_drawer_open

    @rx.event
    def close_history_drawer(self) -> None:
        """Close the history drawer."""
        self.history_drawer_open = False

    @rx.event(background=True)
    async def delete_image_from_db(self, image_id: str) -> AsyncGenerator[Any, Any]:
        """Delete an image from the database and update both lists."""
        async with self:
            user_id = self._current_user_id
            if not user_id:
                logger.warning("Cannot delete image: user not authenticated")
                yield rx.toast.error("Nicht autorisiert.", close_button=True)
                return

            self.deleting_image_id = image_id
        yield

        try:
            logger.info("Deleting image from database: %s", image_id)
            await GeneratedImageRepository.delete(int(image_id), user_id)

            async with self:
                # Remove from both lists
                self.images = [img for img in self.images if img.id != int(image_id)]
                self.history_images = [
                    img for img in self.history_images if img.id != int(image_id)
                ]
                logger.info("Image deleted successfully: %s", image_id)

            yield rx.toast.success("Bild gelöscht.", close_button=True)

        except Exception as e:
            logger.error("Error deleting image: %s", e)
            yield rx.toast.error(f"Fehler beim Löschen: {e!s}", close_button=True)
        finally:
            async with self:
                # Clear loading overlay
                self.deleting_image_id = ""
            yield

    @rx.event
    def add_history_image_to_grid(self, image_id: str) -> None:
        """Add an image from history to the main grid (today's images).

        If the image is already in the grid, do nothing.
        """
        # Check if image is already in grid
        if any(img.id == image_id for img in self.images):
            logger.debug("Image %s already in grid", image_id)
            return
        # Find the image in history
        for img in self.history_images:
            if img.id == image_id:
                # Prepend to grid
                self.images = [img, *self.images]
                logger.info("Added history image %s to grid", image_id)
                break

    @rx.var
    def history_images_by_date(self) -> list[tuple[str, list[GeneratedImageModel]]]:
        """Group history images by date (day).

        Returns list of tuples: (date_label, images_list)
        Sorted by date descending (newest first).
        """
        if not self.history_images:
            return []

        grouped: dict[datetime, list[GeneratedImageModel]] = defaultdict(list)

        for img in self.history_images:
            if img.created_at:
                date_key = img.created_at.date()
                grouped[date_key].append(img)

        # Sort by date descending
        sorted_groups = sorted(grouped.items(), key=lambda x: x[0], reverse=True)

        # Format date labels (deutsch)
        result = []
        month_names = {
            1: "Jan.",
            2: "Feb.",
            3: "März",
            4: "Apr.",
            5: "Mai",
            6: "Juni",
            7: "Juli",
            8: "Aug.",
            9: "Sep.",
            10: "Okt.",
            11: "Nov.",
            12: "Dez.",
        }

        for date_key, imgs in sorted_groups:
            day = date_key.day
            month = month_names[date_key.month]
            year = date_key.year
            date_label = f"{day}. {month} {year}"
            result.append((date_label, imgs))

        return result
